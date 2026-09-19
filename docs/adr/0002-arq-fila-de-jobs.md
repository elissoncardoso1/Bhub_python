# ADR-0002 — ARQ sobre Redis como estratégia de jobs

## Status

Aceito e implementado (Tasks 1–14). O worker real foi validado contra Redis 7 e
PostgreSQL 16 na Task 14 (`tests/integration/test_arq_worker.py`).

## Contexto

A ingestão disparava o trabalho pesado (classificação de artigos, download de PDFs) com
`asyncio.create_task()` dentro do processo do app. As consequências medidas estavam
registradas no relatório de arquitetura: a task morre com o processo, não há retry, não há
observabilidade de fila e não há backpressure — um pico de sync dispara tasks ilimitadas.
O processo web e o trabalho pesado também competiam pelo mesmo event loop.

A restrição de partida: o repositório é async de ponta a ponta (FastAPI + SQLAlchemy
async) e o Redis já era uma dependência operacional plausível. Havia também um caminho
inline em uso na suíte de testes que não podia ser simplesmente apagado.

## Decisão

**ARQ sobre Redis é a estratégia de jobs em produção.** O worker é um processo separado —
`arq app.jobs.tasks.WorkerSettings`, declarado como o serviço `arq-worker` nos dois
composes (`bhub-backend-python/docker-compose.prod.yml:76-114`, `docker-compose.yml:37-64`),
rodando a mesma imagem do `backend`. A configuração central é `WorkerSettings`
(`app/jobs/tasks.py:158-172`): `functions = [task_classify_article, task_download_pdf]`,
`max_jobs = 10`, `job_timeout = 300`, `max_tries = 3`, `retry_jobs = True`,
`keep_result = 86_400`, `health_check_interval = 30`.

A escolha da fila é explícita e fica em um único ponto: `get_task_queue()`
(`app/services/task_dispatcher.py:67-79`) devolve `ArqTaskQueue` quando
`settings.enable_arq` é verdadeiro. `ArqTaskQueue` enfileira em Redis e, em caso de falha,
**propaga** o erro com log estruturado — nunca há degradação silenciosa
(`app/interfaces/task_queue.py:46-59`). Com `ENABLE_ARQ=true` e sem pool inicializado, o
dispatcher levanta `RuntimeError` em vez de executar localmente
(`app/services/task_dispatcher.py:82-89`); o lifespan pré-aquece o pool e, em produção, falha de
conexão no bootstrap é fatal (`app/main.py:56-70`).

`InlineTaskQueue` **não foi removido**: ele é o executor local explícito, permitido apenas
com `ENABLE_ARQ=false`, e executa o trabalho no event loop atual via
`asyncio.create_task` com as tarefas rastreadas em `_pending`
(`app/interfaces/task_queue.py:72-93`). A docstring do módulo declara que esse é o único
ponto do código onde `create_task` é permitido. `close_task_queue()` aguarda as tarefas
inline pendentes antes de encerrar (`app/services/task_dispatcher.py:58-64`).

## Consequências

- O trabalho pesado sobrevive a restart do processo web; o job vive no Redis e é executado
  por outro container.
- Backpressure e limites explícitos: `max_jobs`, `job_timeout`, `keep_result`.
- Observabilidade por job passou a existir: log estruturado e, com telemetria ligada,
  contadores `arq.job.success`/`arq.job.failure`, histograma `arq.job.duration` e span
  `arq.job` (`app/jobs/observe.py`).
- **Negativo — o retry anunciado não existe para os jobs do repositório.** `max_tries = 3`
  e `retry_jobs = True` (`app/jobs/tasks.py:168-169`) nunca disparam, porque o ARQ só
  re-tenta `Retry`/`RetryJob`/`CancelledError` e nenhum código em `app/` levanta essas
  exceções. Uma exceção comum morre no `job_try=1`. O mecanismo foi provado com uma função
  local ao teste, não com os jobs reais (RED-3; ver `CURRENT_ARCHITECTURE.md` § KNOWN RISKS).
- **Negativo — startup caro e dependente de rede.** `startup()` inicializa o
  `EmbeddingClassifier` e carrega os embeddings das categorias a cada subida do worker:
  11,5–13,5 s medidos, mais uma requisição ao HF Hub (`app/jobs/tasks.py:111-119`). Sem o
  modelo, a classificação degrada silenciosamente para a heurística (RED-5).
- **Negativo — dois caminhos de código no fallback inline.** `InlineTaskQueue.dispatch_classification`
  chama `app.services.background_tasks.classify_article_task`, enquanto o job ARQ chama
  `ClassificationService.classify_article` (`app/interfaces/task_queue.py:100-104` vs
  `app/jobs/tasks.py:24-45`). Um teste que esqueça `ENABLE_ARQ=true` mede o caminho errado.
- **Negativo — a ordem commit→dispatch não é atômica.** O job é enfileirado depois do
  `commit` (`app/services/feed_aggregator.py:223`, `:231`, `:238`) sem outbox; um crash na
  janela perde o job (R-01).
- O healthcheck do `arq-worker` é desligado (`docker-compose.prod.yml:100-102`): a
  liveness é do ARQ + política de restart, não do `curl` da imagem.

## Alternativas consideradas

- **Celery.** Rejeitada: modelo de threading, não async/await nativo, e configuração de
  broker mais pesada para o que o projeto precisa. A comparação está no plano de
  refatoração (`BHUB_REFACTORING_PLAN.md`, "Por que ARQ (não Celery)"). Registro: a
  latência de decisão foi a aderência ao stack async, não um benchmark.
- **Manter `asyncio.create_task()` com retry próprio.** Rejeitada: não sobrevive a restart
  do processo e exige reimplementar fila, backpressure e observabilidade.
- **`FastAPI.BackgroundTasks`.** Rejeitada: mesma limitação de vida do processo, sem
  persistência, e ainda acoplada ao ciclo da request.
- **Fila em PostgreSQL (`SELECT ... FOR UPDATE SKIP LOCKED`).** Rejeitada nesta rodada:
  aumentaria a pressão de escrita no banco justamente onde a migração para PostgreSQL
  estava resolvendo contenção; o Redis já existia como dependência operacional.
- **Remover o `InlineTaskQueue`.** Rejeitada: a suíte unitária e os testes de dispatcher
  dependem do caminho local (`tests/unit/test_task_dispatcher.py`), e o executor local é o
  que permite rodar o app sem Redis em desenvolvimento.
