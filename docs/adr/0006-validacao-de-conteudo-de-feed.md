# ADR-0006 — HTTP 200 não basta: validar que a resposta é RSS/Atom

## Status

Aceito e implementado. Corrige o falso sucesso observado em produção em 2026-09-22, com
os feeds da Springer parados desde 2026-08-04 sem nenhum alarme.

## Contexto

`FeedFetcher._classify_response` (`app/services/feed_fetcher.py:136`) classifica como
`FetchStatus.OK` qualquer resposta com status abaixo de 400 que não seja 304. O corpo não
é inspecionado. `FeedAggregatorService.sync_feed` confiava nesse `OK` e, logo após o
`feedparser.parse`, gravava `last_successful_sync_at`, zerava `error_count` e limpava
`last_error` (`app/services/feed_aggregator.py:216-219`, numeração anterior a este ADR),
independentemente de o documento ser ou não um feed.

Editoras científicas passaram a servir os endpoints de RSS atrás de anti-bot. Medido em
produção em 2026-09-22: `link.springer.com/search.rss?...` responde **HTTP 200** com
`Content-Type: text/html` e o corpo `<title>Client Challenge</title>` (desafio da Fastly,
prefixo `/_fs-ch-`); trocar o `User-Agent` não contorna. O `feedparser` devolve zero
entradas, o laço de ingestão não faz nada, e o sync termina marcando sucesso.

O efeito prático é pior que uma falha: o banco passa a afirmar que o feed sincronizou com
sucesso hoje (`error_count = 0`, `last_successful_sync_at` de hoje) enquanto o último
artigo captado é de semanas atrás. Quatro periódicos ficaram ~7 semanas sem ingestão sem
produzir um único erro, log de falha ou incremento de `error_count`.

## Decisão

Um `2xx` só conta como sucesso se o corpo for reconhecível como RSS ou Atom. O critério é
`parsed.version` do `feedparser` — a mesma biblioteca que já fazia o parse, sem parser
próprio e sem custo extra de parsing (`app/services/feed_aggregator.py:189`). Quando ela
vem vazia, `sync_feed` devolve o fluxo ao mecanismo de erro que já existia,
`_record_fetch_failure`, com o novo `FetchStatus.INVALID_CONTENT`
(`app/services/feed_fetcher.py:40`).

Três escolhas dentro dessa decisão merecem registro:

**O `Content-Type` não é o critério.** Servidores erram o header em feeds válidos, e o
desafio da Fastly poderia perfeitamente servir HTML com `application/rss+xml`. Validar o
documento cobre os dois casos; validar o header cobre nenhum com segurança.

**`bozo` não é o critério.** `bozo` responde "o parse teve avisos", não "isto não é um
feed": um RSS estruturalmente válido com um problema menor (encoding declarado errado,
entidade XML solta) vem com `bozo=True` e `version='rss20'`, e ingere normalmente. Medição
sobre os 40 feeds cadastrados em 2026-09-22: nenhum está hoje nessa condição — os 21 que
ingerem têm `bozo=False` —, então os dois critérios coincidem no dado atual. `version` é
escolhido por responder à pergunta certa, e por não derrubar o primeiro feed levemente
malformado que apareça. (O "Spectrum News" é `bozo=True`, mas com `version` vazia e zero
entradas: é um dos feeds quebrados que esta mudança passa a reprovar, não um contraexemplo.)

**Feed válido com zero itens continua sendo sucesso.** Um RSS ou Atom bem formado sem
`<item>` mantém `version` preenchida (`rss20`, `atom10`) e segue pelo caminho de sucesso.
Só documento não-reconhecível — HTML, JSON, corpo vazio — é falha. A distinção é o ponto
inteiro deste ADR: "zero artigos" não é sintoma de nada; "zero artigos porque a resposta
não era um feed" é.

O acesso é `parsed.get("version")`, não `parsed.version`: com corpo vazio o `feedparser`
sequer cria a chave, e o acesso por atributo levanta `AttributeError`, que cairia no
`except Exception` genérico do `sync_feed` e gravaria uma mensagem de erro inútil
("object has no attribute 'version'") em vez do diagnóstico real.

## Consequências

`_record_fetch_failure` (`app/services/feed_aggregator.py:460`) já fazia exatamente o que
se precisa, e não foi alterado: preserva `last_successful_sync_at`, grava `last_error`,
incrementa `error_count` (porque `INVALID_CONTENT` não é `TRANSIENT_ERROR`) e devolve
`success=False`. Nenhuma migração: os campos reutilizados já existem.

Os quatro feeds da Springer passam a acumular `error_count` a cada ciclo e a aparecer como
falhos — que é o estado verdadeiro. `last_successful_sync_at` deles para de avançar e volta
a apontar a data do último sucesso real, tornando o problema mensurável por consulta.

Isso expõe, sem resolver, uma segunda falha já registrada como follow-up: JABA, JEAB e
JOBM estão com `error_count = 16` contra `max_errors = 5` e seguem `is_active = true` — a
desativação por excesso de erros não está surtindo efeito. Os feeds da Springer vão entrar
na mesma condição. Corrigir o `max_errors` é trabalho separado, deliberadamente fora deste
ADR.

Este ADR **não** restaura a ingestão dos periódicos: ele faz a falha aparecer. Recuperar o
conteúdo exige tratar as fontes (APIs como Crossref/OpenAlex no lugar do RSS das editoras),
e isso é uma decisão arquitetural própria.

## Alternativas consideradas

**Tratar `0 entradas` como falha.** Simples e errado: apagaria a diferença entre um feed
saudável numa semana sem publicações e um endpoint bloqueado. Geraria alarme falso
recorrente nos periódicos acadêmicos, que passam meses sem edição nova — exatamente os
feeds que este ADR quer proteger.

**Validar pelo `Content-Type`.** Rejeitado acima: falha nos dois sentidos, e a correção
teria que ser refeita no primeiro anti-bot que devolvesse o header certo.

**Validar no `FeedFetcher`, junto de `_classify_response`.** Centralizaria a regra no ponto
do HTTP, mas obrigaria a parsear o feed duas vezes — uma no fetcher para validar, outra no
agregador para ingerir. O agregador já tem o documento parseado na mão; validar ali custa
uma comparação.

**Contornar o anti-bot** (browser headless, impersonação mais agressiva). Fora de escopo e
de má política: trata o sintoma, briga com a editora e deixa a ingestão dependente de uma
corrida armamentista. O `FetchStatus.BLOCKED` já existe justamente para registrar que a
fonte recusou acesso.
