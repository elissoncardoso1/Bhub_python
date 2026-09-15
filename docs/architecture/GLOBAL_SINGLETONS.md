# Decisões sobre Singletons Globais — BHub v1.1 (T2.5, Task 8)

> **Status:** ATIVO · **Escopo:** `bhub-backend-python/app` · **Data:** 2026-09-15
> Task 8 do plano BHub v1.1 — Production Reliability (épico 2, T2.5).
> Complemento de [SERVICE_INSTANTIATION_MAP.md](SERVICE_INSTANTIATION_MAP.md) (task 5):
> este documento resolve as decisões deixadas em aberto no mapa, seções 1.9–1.12 e 1.15.

## Critério de aceite avaliado

> "Não há estado global mutável desnecessário." (épico 2, DI)

Regra aplicada, conforme o épico:

- Serviço com **apenas configuração imutável e comportamento stateless** (toda I/O
  chega por argumento) → **MANTER o global**, documentando a decisão.
- Serviço que **guarda dependência de DB/clock/storage no próprio objeto** →
  **REMOVER o singleton global**, injetando via provider/factory.
- **Cache intencional** de recurso caro (modelo de IA/ML, pool de conexão),
  imutável após a inicialização e com ciclo de vida controlado → **MANTER**:
  não é "estado global mutável desnecessário", é infraestrutura.
- Helper/global **sem call sites** (código morto) → **REMOVER**.

---

## Decisões

### 1. `refresh_token_service` — MANTER

| Item | Valor |
|---|---|
| Onde | `app/core/refresh_token.py:285` (`refresh_token_service = RefreshTokenService()`) |
| Estado no `__init__` | Apenas `self.cookie_name = "refresh_token"` e `self.token_length = 64` (l.25-27) — **configuração imutável** |
| I/O no objeto | **Nenhum.** Todos os métodos que tocam persistência recebem `db: AsyncSession` como argumento (`create_refresh_token`, `refresh_access_token`, `revoke_refresh_token`); JWT usa `settings` (leitura); cookies operam sobre `Request`/`Response` recebidos por parâmetro |
| Consumidores | `app/web/auth.py` (login/logout web), `app/api/auth/__init__.py` (login/logout/refresh API) e os helpers do próprio módulo (`get_refresh_token_from_request`, `validate_and_refresh_token`) |

**Justificativa contra o critério:** o objeto não guarda estado mutável — é
stateless com configuração fixa definida no construtor. Converter para
`Depends()` exigiria tocar 3 módulos consumidores para ganho zero de
testabilidade (não há I/O escondida; a sessão já trafega como argumento `db`,
que as rotas já recebem via `Depends`). A instância global funciona aqui como
namespace de funções, não como estado.

**Exceção futura:** se `cookie_name`/`token_length` passarem a vir de
`settings` (configuráveis por ambiente), migrar para provider em
`app/api/deps.py` na mesma mudança.

### 2. `_ai_manager` / `get_ai_manager()` — MANTER como lazy singleton (facade)

| Item | Valor |
|---|---|
| Onde | `app/ai/manager.py:449-456` |
| Estado | `_ai_manager: AIManager \| None`; inicializado 1× sob demanda; providers são criados no `_setup_providers` (init) e não mudam depois — **imutável após init** |
| I/O | Rede via `httpx.AsyncClient` **por chamada** dentro dos providers (não retido no singleton) |

**Justificativa:** singleton de fachada com contrato `IAIManager` já substituível
em testes (`deps.get_ai_manager` / `AIDep`). O problema apontado no mapa
(1.10) não é o global em si, mas os **call sites que contornam o provider** —
migração gradual documentada como follow-up (seção "Follow-ups").

### 3. `_llm_instance` — MANTER (cache de modelo)

| Item | Valor |
|---|---|
| Onde | `app/ai/local_llm_service.py:21,115-148` |
| Estado | Global `Llama \| None` com lock e double-checked — cache intencional do modelo local carregado de GGUF |

**Justificativa:** carregar o modelo é caro (leitura de disco/potencial
download); o global é **imutável após o primeiro preenchimento** e interno ao
`LocalLLMService`. Caso legítimo de cache, não de estado mutável de serviço.

### 4. `_model_manager` / `get_model_manager()` — MANTER (cache de modelos)

| Item | Valor |
|---|---|
| Onde | `app/ai/model_manager.py:245-252` |
| Estado | Lazy singleton; I/O (fs + HuggingFace) só na descoberta/download de modelos |
| Consumidores | Apenas `LocalLLMService` (`local_llm_service.py:99,111`) |

**Justificativa:** mesmo padrão do item 3 — cache imutável-após-init de recurso
caro, sem exposição em rotas. Segue a recomendação do mapa (1.11).

### 5. `EmbeddingClassifier` (singleton `__new__`) — MANTER; `get_classifier()` — REMOVIDO

| Item | Valor |
|---|---|
| Onde | `app/ml/embedding_classifier.py:19` (`__new__` singleton com estado de classe `_model`, `_initialized`) |
| Estado | Estado de classe é **cache do `SentenceTransformer`** (download no primeiro `initialize()`), com guarda idempotente (`if cls._initialized: return`) |

**Justificativa (singleton):** modelo de embedding caro, caso legítimo de cache;
já substituível em teste via classmethod `classify`. Segue recomendação do mapa (1.12).

**Decisão sobre `get_classifier()` (mapa 1.12, "LEGACY a decidir"):** helper
`async def get_classifier()` em `embedding_classifier.py:298` **sem nenhum call
site** em `app/` e `tests/` (verificado por grep nesta task). Manter dois
caminhos de inicialização — `initialize()` (usado) e `get_classifier()` (morto)
— contradiz o critério e o item "Nenhuma abstração foi criada sem caso de teste
ou necessidade concreta". **Removido nesta task.**

`HeuristicClassifier` (mapa 1.12) é PURE estático, sem instanciação — nada a
decidir.

### 6. `limiter` (slowapi) — MANTER

| Item | Valor |
|---|---|
| Onde | `app/core/limiter.py:10` |

**Justificativa:** a API do slowapi exige uma instância de `Limiter` em nível de
módulo, registrada no app (`app.state.limiter` + exception handler). O estado
in-memory de contadores é do rate limiter, não da aplicação. Padrão de
biblioteca; alternativa exigiria fork do slowapi.

### 7. `scheduler` (APScheduler) — MANTER

| Item | Valor |
|---|---|
| Onde | `app/jobs/scheduler.py:14` |

**Justificativa:** singleton de **infraestrutura** com ciclo de vida
controlado (`setup_scheduler`/shutdown em `app/main.py`). A mutabilidade
(adicionar/remover jobs) é a função do objeto, e ele não é compartilhado com a
camada de serviços.

### 8. `_arq_pool` / `_inline_queue` — MANTER

| Item | Valor |
|---|---|
| Onde | `app/services/task_dispatcher.py:22-23` |

**Justificativa:** design T1.1/T1.2 — fila explícita com fail-fast em produção,
sem fallback silencioso. Os globais são o próprio mecanismo de dispatch,
inicializados sob demanda e fechados em `close_task_queue()` no shutdown.

### 9. Sink de alerta (`httpx.Client` em `create_alert_sink`) — MANTER

| Item | Valor |
|---|---|
| Onde | `app/core/alerting.py:20` |

**Justificativa:** infraestrutura de logging, criada 1× em `setup_logging`,
fora do fluxo de request, best-effort por design. Não é estado de serviço.

### 10. `background_tasks.classify_article_task` — MANTER, marcar como LEGADO a deprecar

| Item | Valor |
|---|---|
| Onde | `app/services/background_tasks.py:12` |
| Situação | Duplica a lógica de classificação do job ARQ `task_classify_article` (`app/jobs/tasks.py:25`); ainda é o executor do `InlineTaskQueue.dispatch_classification` (`app/interfaces/task_queue.py:101`) em dev/test |

**Justificativa:** o fluxo está vivo (fila inline em dev/test) e coberto por
testes; removê-lo agora quebraria o contrato `ITaskQueue` sem substituto pronta.
Não é singleton — é caminho legado. A convergência para a operação
transacional do job ARQ (como feito para PDF na T2.2:
`PDFService.process_article_pdf`) fica registrada como follow-up.

---

## Resumo

| Global | Decisão | Mudança de código |
|---|---|---|
| `refresh_token_service` | **MANTER** — stateless, config imutável | Não |
| `_ai_manager` (lazy) | **MANTER** — facade imutável pós-init | Não |
| `_llm_instance` | **MANTER** — cache de modelo caro | Não |
| `_model_manager` (lazy) | **MANTER** — cache de modelos | Não |
| `EmbeddingClassifier` (singleton) | **MANTER** — cache de modelo caro | Não |
| `get_classifier()` | **REMOVER** — helper sem call sites | Sim (removido) |
| `limiter` (slowapi) | **MANTER** — padrão da biblioteca | Não |
| `scheduler` (APScheduler) | **MANTER** — infra com ciclo de vida no main | Não |
| `_arq_pool` / `_inline_queue` | **MANTER** — mecanismo T1.1/T1.2 | Não |
| Sink de alerta | **MANTER** — infra de logging best-effort | Não |
| `classify_article_task` (background_tasks) | **MANTER + deprecar** — legado vivo | Não (follow-up) |

Conclusão contra o critério do épico: os globals mantidos são ou (a)
stateless com configuração imutável (`refresh_token_service`), ou (b) caches
intencionais imutáveis-após-init (`_llm_instance`, `_model_manager`,
`EmbeddingClassifier`, `_ai_manager`), ou (c) infraestrutura imposta pelo
framework/biblioteca com ciclo de vida controlado (`limiter`, `scheduler`,
`_arq_pool`/`_inline_queue`, sink de alerta). O único estado global
desnecessário encontrado — o helper morto `get_classifier()` — foi removido.

## Follow-ups (fora do escopo desta task)

1. Migrar call sites de `get_ai_manager()` para `AIDep`/parâmetro:
   `app/api/v1/ai.py:70,161,198`, `app/web/translation.py:62`,
   `app/services/background_tasks.py:43`, `app/ml/impact_rating.py:87`.
2. Convergir `classify_article_task` (inline) para a operação transacional do
   job ARQ (paridade com o que T2.2 fez para PDF) e deprecar
   `app/services/background_tasks.py`.