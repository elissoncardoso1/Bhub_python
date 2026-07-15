# Design: Resiliência da ingestão de feeds RSS (Opção A)

**Data:** 2026-07-04
**Status:** Aprovado (Opção A do brainstorming baseado em `docs/rss/rss_research.md`)
**Escopo:** `bhub-backend-python/` — camada de fetch e política de erros do pipeline de feeds

## Problema

Dos ~35 feeds cadastrados, 7 falham de forma recorrente. Consulta à tabela `feeds` mostra que
**todos os erros são de camada HTTP**, não de parsing:

| Erro | Feeds afetados | Causa raiz |
|---|---|---|
| 403 Forbidden | Autism Parenting Magazine, ABA Fora da Mesinha, Brighter Strides ABA | Anti-bot (WAF/Cloudflare) detecta o fingerprint TLS do httpx |
| 404 / 410 Gone | Blog ABAEDU, Revista Perspectivas, JOBM (T&F) | URL do feed mudou ou foi removida — retry não resolve |
| 502 Bad Gateway | ABA Everyday Blog | Transitório, mas conta no `error_count` como permanente |

Problemas estruturais que amplificam os erros:

1. **Morte permanente**: `Feed.needs_sync` retorna `False` para sempre quando
   `error_count >= max_errors` (5). Cinco feeds já estão mortos sem recuperação automática.
2. **`custom_headers` nunca aplicado**: a coluna existe no modelo mas `FeedAggregatorService.sync_feed`
   faz `get(feed.feed_url)` sem usá-la.
3. **Sem conditional GET nem retry**: o aggregator baixa o feed inteiro toda hora (sem
   ETag/Last-Modified) e não usa `tenacity` (o `web_scraper.py` já usa).

A pesquisa (`docs/rss/rss_research.md`) confirma que a stack base (feedparser + httpx +
APScheduler) é a arquitetura correta para o porte atual. A migração adequada é endurecer a
camada de fetch, não trocar de framework.

## Decisão

Endurecimento incremental em cinco frentes, adotando duas bibliotecas da pesquisa
(`trafilatura`, `curl_cffi`):

### 1. Módulo `app/services/feed_fetcher.py` (novo)

Encapsula o fetch resiliente de feeds, testável isoladamente. Interface:

```python
@dataclass
class FetchResult:
    status: FetchStatus        # OK | NOT_MODIFIED | BLOCKED | GONE | TRANSIENT_ERROR
    text: str | None
    etag: str | None
    last_modified: str | None
    error: str | None

class FeedFetcher:
    async def fetch(self, url, *, etag=None, last_modified=None,
                    custom_headers=None) -> FetchResult
```

Comportamento:
- Envia `If-None-Match`/`If-Modified-Since` quando o feed tem `http_etag`/`http_last_modified`
  persistidos; HTTP 304 → `NOT_MODIFIED` (sync sem download).
- Aplica `custom_headers` do feed (JSON) sobre os headers padrão.
- Retry com `tenacity` (3 tentativas, backoff exponencial) apenas para erros de rede/5xx.
- **Fallback anti-bot**: em resposta 403 (ou 429), refaz a requisição via
  `curl_cffi.requests.AsyncSession(impersonate="chrome")`, que replica o fingerprint TLS de
  um navegador real. Só nesse caso — o caminho comum continua no httpx. Se o fallback também
  falhar → `BLOCKED`.
- Classificação do resultado: 404/410 → `GONE`; 403/429 pós-fallback → `BLOCKED`;
  timeout/5xx/rede → `TRANSIENT_ERROR`.

### 2. Política de erros tipada no `FeedAggregatorService`

- `TRANSIENT_ERROR` **não incrementa** `error_count`; apenas registra `last_error` e
  `last_sync_at` (o intervalo normal de sync já funciona como cool-down).
- `BLOCKED` e `GONE` incrementam `error_count`.
- `GONE` dispara redescoberta (item 4) antes de desistir.
- `NOT_MODIFIED` conta como sync bem-sucedido (zera `error_count`).

### 3. Recuperação automática em `Feed.needs_sync`

Substituir a morte permanente por sonda de recuperação: quando `error_count >= max_errors`,
o feed volta a ser elegível se `last_sync_at` for mais antigo que `RECOVERY_PROBE_INTERVAL`
(7 dias). Um sync bem-sucedido zera `error_count` (comportamento já existente).

### 4. Redescoberta de feed em 404/410

Quando `GONE` e o feed tem `website_url`:
1. `trafilatura.feeds.find_feed_urls(website_url)` lista candidatos.
2. Cada candidato é validado: fetch + `feedparser.parse` precisa retornar entradas.
3. Primeiro candidato válido e diferente da URL atual (respeitando a unique constraint de
   `feed_url`) → atualiza `feed.feed_url`, zera `error_count` e loga a mudança.
4. Sem candidato válido → mantém o fluxo de erro normal, registrando em `last_error` que a
   redescoberta falhou.

A redescoberta roda no máximo uma vez por ciclo de sync do feed (sem loop).

### 5. Trafilatura como fallback no `web_scraper.py`

O `WebScrapingService` mantém a extração atual via meta tags `citation_*` (ótimas para
artigos científicos) e seletores; `trafilatura.bare_extraction` entra como **fallback**
quando título ou abstract não forem encontrados pelos seletores. Sem mudança de interface
(`scrape_url` retorna o mesmo dict).

## Mudanças de schema (Alembic)

Novas colunas em `feeds`:

| Coluna | Tipo | Uso |
|---|---|---|
| `http_etag` | `String(255)` nullable | valor bruto do header `ETag` |
| `http_last_modified` | `String(64)` nullable | valor bruto do header `Last-Modified` |

Sem remoção de colunas. `error_count`/`max_errors`/`last_error` mantêm semântica, exceto que
erros transitórios deixam de incrementar o contador.

## Dependências novas

- `trafilatura>=2.0` (Apache-2.0) — extração de texto + `find_feed_urls`
- `curl_cffi>=0.7` (MIT) — impersonação TLS para fallback de 403

## O que fica de fora (decisão explícita)

- **feedparser-rs**: velocidade de parsing não é gargalo com ~35 feeds.
- **Crawlee/Playwright/Celery** (Arquitetura B da pesquisa): overkill; `curl_cffi` resolve os
  403 observados sem custo de navegador headless.
- **MinHash/Datasketch, pgvector, Meilisearch, Crawl4AI**: ortogonais aos erros de feed;
  ficam para quando o RAG/escala entrar no roadmap.

## Tratamento de erros e testes

- Unit tests para: classificação de status no `FeedFetcher` (304, 403→fallback, 404/410,
  5xx/timeout, sucesso), aplicação de `custom_headers`, política de `error_count` no
  aggregator, `needs_sync` com sonda de recuperação, validação de candidatos na redescoberta,
  fallback trafilatura no scraper.
- HTTP mockado (`respx` ou monkeypatch do client); `curl_cffi` e `trafilatura` mockados nos
  testes de unidade para não depender de rede.
- Critério de sucesso operacional: após deploy, os 3 feeds 403 voltam a sincronizar via
  fallback; os feeds 404 com `website_url` válido são redescobertos ou marcados com
  `last_error` explícito; nenhum feed permanece morto por erro transitório.
