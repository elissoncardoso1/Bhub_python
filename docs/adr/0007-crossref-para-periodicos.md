# ADR-0007 — Periódicos científicos passam a ser ingeridos pela API do Crossref

## Status

Aceito e implementado. Complementa o ADR-0006: aquele fez a falha silenciosa aparecer,
este troca a fonte para recuperar a ingestão. Medição de apoio em 2026-09-25 sobre os 11
feeds com `journal_name IS NOT NULL` da tabela `feeds`.

## Contexto

Sete dos onze feeds de periódicos estão sem coletar, e nenhum deles é um defeito de parsing
do BHUB:

| Grupo | Periódicos | Sintoma |
| --- | --- | --- |
| Springer | BAP, Perspectives on Behavior Science, The Analysis of Verbal Behavior, Behavior and Social Issues | HTTP 200 com HTML de challenge da Fastly, 0 itens. Silencioso até o ADR-0006 |
| Wiley | JABA, JEAB | HTTP 403 mesmo com impersonação TLS (`curl_cffi`), `error_count = 16`, nunca sincronizaram |
| Taylor & Francis | JOBM | Idem Wiley |

O bloqueio é de infraestrutura anti-bot das editoras, não de formato. A tentativa de
contornar (impersonação de fingerprint TLS, `User-Agent` de navegador) já estava
implementada em `FeedFetcher._fetch_impersonated` e falha nos três casos — os 403
persistem. Insistir nesse caminho é uma corrida armamentista: a cada endurecimento do
WAF o feed para de novo, e o custo é pago em produção, não em teste.

O conteúdo, porém, **está disponível por uma via pública e estável**: as três editoras
depositam metadados no Crossref, que expõe uma API REST sem autenticação, indexada por
ISSN, operada pela infraestrutura acadêmica (não é scraping de site de editora).

## Decisão

Periódicos passam a ser ingeridos pela **API REST do Crossref**
(`GET https://api.crossref.org/journals/{ISSN}/works`), reaproveitando o pipeline de
artigos que já existe. RSS continua sendo a fonte de blogs e portais — ali funciona e não
há motivo para trocar.

O modelo `Feed` ganha duas colunas (`app/models/feed.py`):

- `journal_source` (`FeedJournalSource`: `RSS` \| `CROSSREF`), default `RSS`;
- `issn` (`String(12)`, anulável) — a chave de consulta no Crossref.

O roteamento acontece em `FeedAggregatorService.sync_feed`, que delega a
`_sync_crossref_feed` quando `journal_source == CROSSREF`, e mantém o caminho RSS
intocado em todos os outros casos.

### Por que reaproveitar o `ArticleParserService` em vez de um parser novo

O adaptador (`app/services/crossref_source.py`) **não** cria um formato intermediário
próprio: ele normaliza cada work para o mesmo dicionário que o `feedparser` produz
(`id`, `link`, `title`, `summary`, `published`, `authors`, `prism_publicationname`,
`language`, `license`) e o entrega ao `ArticleParserService.parse_entry` que já existe.
Consequências:

- Zero parser duplicado. Toda a limpeza de HTML/entidades, o desmembramento de autores,
  a remoção de prefixos de título e a heurística de idioma continuam em um só lugar.
- `generate_external_id` produz o mesmo `feed_{feed_id}_{md5}` de sempre, agora com
  `id = "doi:{doi}"` como semente — o identificador passa a ser o DOI, estável entre
  execuções e independente de o item mudar de posição na resposta.
- A deduplicação por `external_id` do `_process_feed_entry` (já existente) resolve o
  problema das republicações: a Wiley publica Early View e depois o número fechado, e o
  mesmo DOI reaparece com metadados levemente diferentes. Com o DOI como semente do
  `external_id` o segundo item é ignorado, sem precisar de índice novo.

### Por que `SourceType.RSS` nos artigos do Crossref

A tentação é criar `SourceType.CROSSREF`. Não foi feito porque `SourceType` é contrato
público e atravessa filtros de listagem (`app/web/routes.py`, `app/api/v1/articles.py`)
que separam portais de periódicos por `source_type IN (RSS, SCRAPING)`. Um valor novo
ficaria **fora** desses filtros e os artigos migrados sumiriam das páginas — regressão
silenciosa de UI em troca de pureza semântica. A distinção portal/periódico continua
sendo feita por `journal_name` (`ArticleResponse.source_category`), que os artigos do
Crossref têm preenchido.

### Por que não mapear `pdf_url`

O campo `link` do Crossref aponta, na maioria dos casos, para o PDF hospedado na editora —
exatamente o host que responde 403. Mapeá-lo faria o pipeline enfileirar downloads
`dispatch_download_pdf` que só podem falhar, gastando banda e ampliando a superfície de
bloqueio de IP. **Artigos do Crossref não trazem `pdf_url`.** `is_open_access` é
preenchido apenas quando há licença Creative Commons explícita (`license` do Crossref),
para não marcar como aberto conteúdo pago.

### Sem `CrossrefStatus` próprio para cada erro HTTP

O adaptador classifica as respostas nos mesmos conceitos do `FetchStatus` já existente
(`OK`, `INVALID_CONTENT`, `BLOCKED`, `TRANSIENT_ERROR`, `NOT_MODIFIED`), e devolve um
`FetchResult`. Isso permite que `_record_fetch_failure` — o mecanismo de erro validado
pelo ADR-0006 — trate as falhas do Crossref sem nenhum ramo novo: preserva
`last_successful_sync_at`, grava `last_error` e incrementa `error_count`. Um `404` de ISSN
vira `INVALID_CONTENT` (falha permanente, incrementa) e um `429` vira `TRANSIENT_ERROR`
(não incrementa, por ser limite de taxa e não defeito da fonte).

### Janela incremental e idempotência

A consulta usa `filter=from-pub-date:{último_sucesso - lookback},until-pub-date:hoje,
type:journal-article`, com `sort=published&order=desc`. O `until` existe para não capturar
registros com data futura, comuns em depósito antecipado. A sobreposição de `lookback`
(90 dias no primeiro sync, 7 dias nos seguintes) é intencional e inofensiva: o
`external_id` derivado do DOI descarta o que já entrou.

`rows` (`CROSSREF_ROWS`, 100) com paginação por `offset` até um teto de páginas
(`CROSSREF_MAX_PAGES`, 3) limita o trabalho de um único feed a 300 works por execução.
Periódicos de comportamento não chegam perto disso numa janela de 90 dias — JABA
depositou 39 works em 2026.

### Cota e identificação

O Crossref tem pool público (~1 req/s anônimo) e pool "polite" (~3 req/s) para clientes
que se identificam. O adaptador envia `User-Agent` e `mailto` configuráveis
(`CROSSREF_USER_AGENT`, `CROSSREF_MAILTO`) e um timeout próprio
(`CROSSREF_TIMEOUT_SECONDS`). O teto de páginas por feed mantém a carga previsível mesmo
numa instalação mal configurada, e a sincronização é sequencial (um feed por vez), então a
cadência efetiva fica bem abaixo do limite do pool.

## Consequências

**Recupera ingestão sem tocar em WAF.** Os sete feeds recebem conteúdo novo pelo DOI, com
autores e abstract quando depositados. Nenhuma requisição volta a bater nos hosts
bloqueados nesses periódicos.

**A cobertura passa a depender do depósito na editora.** Crossref só devolve o que a
editora deposita; para conteúdo muito recente, o RSS (quando funciona) pode adiantar em
dias. Em troca, ganha-se estabilidade e um contrato de dados documentado. É um trade-off
explícito: prefere-se dado que chega três dias depois a dado que não chega.

**`volume`, `issue` e `pages` não são mapeados.** O Crossref os oferece e o modelo
`Article` tem as colunas, mas nenhuma outra fonte as preenche hoje e `parse_entry` não as
lê. Preencher só para o Crossref criaria assimetria entre fontes; fica como melhoria
aplicável a todas de uma vez.

**Abstract não é garantido.** A editora deposita o abstract quando quer; muitos itens do
Crossref vêm só com título e DOI. O artigo entra sem resumo — melhor que não entrar. O
enriquecimento por outra fonte (PubMed, OpenAlex) fica como follow-up, não como requisito.

**`is_open_access` fica conservador.** Artigos sem licença explícita ficam `False` mesmo
quando são abertos na prática. Prefere-se subestimar a marcar conteúdo pago como aberto.

**Desativação por `max_errors` (D2) passa a surtir efeito — e isso obrigou a corrigir a
sonda de recuperação.** `sync_all_active_feeds` filtrava `is_active == True`; desativar o
feed o excluía da consulta, e a sonda semanal de `Feed.needs_sync` — que existe justamente
para não transformar erro em morte permanente (ADR do plano de resiliência de 2026-07-04) —
nunca era alcançada para um feed desativado por erro.

A primeira tentativa de reconciliar as duas coisas incluía feeds com
`error_count >= max_errors` na consulta e mantinha a sonda válida para eles. Isso **não
fechava o ciclo**: um sync bem-sucedido zerava `error_count`, e com o contador em zero o
feed deixava de ser elegível — mas continuava `is_active=false`, logo fora da rotação para
sempre. A "sonda de recuperação" recuperava o contador, não o feed.

A correção é um marcador explícito, `feeds.deactivated_by_errors` (bool, default `false`).
Ele distingue os dois motivos possíveis de um feed estar inativo, que antes eram
indistinguíveis:

| `is_active` | `deactivated_by_errors` | Significado | Sonda? |
| --- | --- | --- | --- |
| `true` | irrelevante | Normal | Não — segue a frequência configurada |
| `false` | `true` | Desativado automaticamente por erro | Sim, a cada 7 dias |
| `false` | `false` | Desativado pela curadoria | Não, nunca |

Com o marcador, um sync bem-sucedido na sonda reativa o feed (`is_active=true`,
`deactivated_by_errors=false`, `error_count=0`). Curadoria continua soberana: desativar um
feed pelo admin grava `deactivated_by_errors=false`, e nenhum código reativa o que um humano
deliberadamente desligou.

Como isso significa que o conjunto de feeds sincronizados pode crescer (feeds antes
"condenados" voltam a entrar), a sincronização continua sequencial e limitada por
`CROSSREF_MAX_PAGES`, mantendo a carga previsível.

**Efeito colateral visível:** feed desativado some da rota pública `/api/v1/feeds` (que
filtra `is_active`). Para os três da Wiley e o OBM Network News — que nunca ingeriram nada
— isso é uma melhoria de curadoria. O admin continua vendo todos. Note que um feed
**reativado** volta a aparecer publicamente: é o comportamento desejado, mas a curadoria
deve saber que a lista pública pode mudar sozinha depois de uma recuperação.

## Alternativas consideradas

**Continuar com RSS e reforçar a impersonação.** Rejeitado. Já falha contra Wiley e T&F
com `curl_cffi` em modo `chrome`; escalar para browser headless só aumenta acoplamento com
o WAF da editora e o custo operacional (Chromium em VPS de produção), sem garantia de
durabilidade. É tratar sintoma.

**OpenAlex.** Cobertura melhor e abstracts com mais frequência, mas a chave de API passou
a ser obrigatória (13/02/2026) e o uso gratuito é limitado por cota diária. Adiciona uma
credencial e um limite a mais para o mesmo conteúdo. Fica como fonte de enriquecimento
futuro, não como fonte primária.

**PubMed E-utilities.** Ótimo para abstracts de conteúdo indexado, mas cobre mal as
revistas de análise do comportamento brasileiras (REBAC, RBTCC, Acta Comportamentalia),
que são justamente as que se pretende ampliar. Complementar, não primário.

**RSS Elsevier (`rss.sciencedirect.com`).** Funciona e não exige chave, mas resolve um
único editor e mantém o acoplamento a scraping de site de editora que motivou este ADR.

**Tabela `journals` própria, com os works em tabela separada.** Modelagem mais limpa no
papel, mas duplica a noção de "artigo" (que já tem `journal_name`, `doi`, `feed_id`) e
exigiria juntar duas origens na UI. Reaproveitar `feeds` + `articles` mantém uma única
lista de artigos e uma única tela de curadoria.

**Guardar `volume`/`issue`/`pages` do Crossref.** O dado existe e o modelo `Article` já tem
as colunas, mas `parse_entry`/`_process_feed_entry` não as preenchem hoje para nenhuma
fonte. Preencher só para o Crossref criaria assimetria entre fontes. Fica como follow-up
(aplicável a todas as fontes de uma vez).
