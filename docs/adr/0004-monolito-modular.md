# ADR-0004 — Monolito modular com dependências explícitas

## Status

Aceito e implementado (Tasks 1–3). Continua em vigor.

## Contexto

O relatório de arquitetura de 06/mai/2026 (`bhub-backend-python/ARCHITECTURE_REPORT.md`,
documento **histórico**) apontava, como segundo débito, o acoplamento a implementações
concretas: rotas instanciavam serviços diretamente, alguns serviços abriam a própria sessão
de banco por dentro (`get_session_context`) e um serviço recebia o banco por parâmetro
implícito, o que impedia substituí-lo em teste.

## Decisão

Manter **um único processo FastAPI** (sem microserviços, sem broker de domínio) e
organizá-lo como monolito modular de camadas, com as dependências entrando pela composição
do FastAPI:

- Portas: `app/interfaces/services.py` declara `IClassificationService`, `ISearchService`,
  `IFeedAggregator` e `IAIManager` como `Protocol` (`:16`, `:31`, `:53`, `:62`);
  `app/interfaces/task_queue.py:28` declara `ITaskQueue`.
- Composition root: `app/api/deps.py` (`get_ai_manager` `:63`, `get_classification_service`
  `:70`, `get_search_service` `:80`, `get_pdf_service` `:87`, `get_opengraph_service` `:99`,
  `get_feed_aggregator_service` `:111`), consumidas por `Depends` e substituíveis por
  `app.dependency_overrides` nos testes.
- Rotas: `app/api/v1` (JSON) e `app/web` (HTML), agregadas por `app/web/router.py:14-18`
  (`auth`, `admin`, `public`, `consent`, `translation`), montadas em `app/main.py`.
- Exceção assumida: o `EmbeddingClassifier`/`HeuristicClassifier` de `app/ml` é importado
  de forma tardia dentro do serviço (`app/services/classification_service.py:58`), para não
  pagar o custo do modelo na importação do app.

## Consequências

- Positivo: serviços testáveis por injeção — a suíte unitária substitui IA, fila e banco sem
  tocar as rotas; trocar a implementação de fila (ARQ ↔ inline, ADR-0002) não exige mudar
  chamadores.
- Positivo: o pipeline de feeds/PDF passou a rodar fora do ciclo de request sem duplicar
  regra de negócio.
- Negativo: as portas **não** cobrem todos os serviços — `get_pdf_service` e
  `get_opengraph_service` devolvem tipos concretos (`app/api/deps.py:87`, `:99`), então
  esses dois ainda não têm contrato formal.
- Negativo: o custo de tipo é real e está declarado — o ratchet de mypy registra **127
  erros em 28 arquivos** (`pyproject.ratchet.toml`), dívida de tipagem do processo inteiro
  que este ADR não resolve.
- Negativo: um único deploy acopla web, API, worker e scheduler; não há escalonamento
  independente por camada.

## Alternativas consideradas

- **Microserviços por domínio** (feed / IA / busca): rejeitada — o volume atual não justifica
  custo operacional, e cada serviço reabriria o problema de contrato que as portas já
  resolvem dentro do processo.
- **Camadas clássicas sem `Protocol`** (só serviços concretos): rejeitada — mantém o
  acoplamento que motivou o débito e impede `dependency_overrides` tipado.
- **Service locator / container de DI externo**: rejeitada — o `Depends` do FastAPI já cobre
  o caso e a substituição em teste é nativa; um container adicionaria um framework sem
  ganho.
- **Manter a sessão de banco criada dentro de cada serviço**: rejeitada — foi exatamente a
  causa do débito em `get_opengraph_service` (nota em `app/api/deps.py:99-107`).
