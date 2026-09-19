# ADR-0005 — Estratégia de IA: multi-provedor com degradação para ML local

## Status

Aceito e implementado. Continua em vigor, com um risco de custo de startup registrado
(R-04 em `CURRENT_ARCHITECTURE.md`).

## Contexto

A classificação de artigos precisa rodar em lote e sem intervenção, em dois cenários com
restrições opostas: (a) produção com chave de API configurada, onde o custo por chamada
importa; (b) ambientes sem chave (dev, CI, testes), onde não pode haver dependência de rede
externa. A tradução de título/resumo também precisa de cache, porque reprocessar o mesmo
texto custa chamada de API a cada requisição de página.

## Decisão

Uma cadeia explícita de degradação, com o caminho local **antes** do provedor pago como
último recurso da classificação:

1. `app/ai/manager.py` é a fachada (`AIManager`), que monta o dicionário de provedores em
   `_setup_providers` (`:38-62`) — um provedor só entra se a configuração correspondente
   existir (`:43-45` local, `:53` DeepSeek, `:57` OpenRouter, `:61` HuggingFace).
2. Ordem de tentativa na **classificação** (`:71-76`): DeepSeek → LocalLLM → OpenRouter →
   HuggingFace, com `record_ai_fallback` registrado a cada troca (`:98-100`).
3. Ordem na **tradução** (`:114-118`): DeepSeek → LocalLLM → OpenRouter (sem HuggingFace).
4. Se a IA não produzir classificação utilizável, `ClassificationService.classify` cai para
   `EmbeddingClassifier` (modelo local `paraphrase-multilingual-MiniLM-L12-v2`,
   `app/config.py:129`) e, em seguida, para `HeuristicClassifier` por palavras-chave; o
   retorno neutro é `("outros", 0.0)` (`app/services/classification_service.py:58-71`).
5. Tradução é cacheada em banco (`app/models/translation_cache.py`, tabela
   `translations_cache` — `:17`) e consumida por `app/web/translation.py:55-68` e por
   `app/api/v1/ai.py`; reprocessar o mesmo texto não reincide em chamada de API.

## Consequências

- Positivo: o sistema classifica com zero provedor configurado — a suíte unitária e o CI não
  tocam rede externa, e a heurística garante resposta mesmo se o modelo local falhar.
- Positivo: a troca de provedor é dado de configuração (`settings`), não código; cada salto
  de provedor é observável via telemetria (`record_ai_fallback`).
- Negativo (R-04): o worker carrega o modelo de embeddings **e** os embeddings das
  categorias no `startup()`, custando ~11,5–13,5 s de subida e uma requisição ao HF Hub
  (`app/jobs/tasks.py:111-119`). Subida lenta e dependência de rede no boot não são
  gratuitas.
- Negativo: se `EmbeddingClassifier` não estiver inicializado, a classificação **degrada em
  silêncio** para a heurística — não há alarme de degradação, apenas log.
- Negativo: não existe medição de acurácia da classificação no repositório; a qualidade da
  cadeia é julgada por comportamento, não por métrica publicada.
- Negativo (R-05): o `POST /api/v1/ai/translate` não tem rate limit efetivo — o slowapi
  procura o parâmetro `request` e o endpoint o nomeia como corpo Pydantic
  (`app/api/v1/ai.py:106-112`). Custo de tradução sem teto por usuário.

## Alternativas consideradas

- **Um único provedor pago (DeepSeek) com falha dura**: rejeitada — quebraria o CI/dev sem
  chave e faria a classificação em lote depender de disponibilidade externa.
- **Só ML local (embeddings), sem LLM**: rejeitada — a heurística e o classificador local não
  cobrem categorias novas nem confiança calibrada; a LLM é o único caminho com categoria
  arbitrária.
- **Fila de classificação com retry infinito em vez de degradação**: rejeitada — troca uma
  resposta pior por nenhuma resposta; o artigo ficaria sem categoria indefinidamente.
- **Recarregar o modelo de embeddings de forma preguiçosa (no primeiro job, não no
  `startup`)**: considerada, **não implementada** — reduziria a subida do worker, mas move a
  latência para o primeiro artigo de cada processo; decisão adiada, não tomada.
