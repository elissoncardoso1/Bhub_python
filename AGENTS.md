# AGENTS.md — contexto para agentes de código (BHub)

Este arquivo é a porta de entrada para qualquer agente (Claude Code, Codex, Cursor, outro)
que trabalhe neste repositório. Ele diz **o que ler primeiro** e **o que não assumir**.

## Leia primeiro (referência única da arquitetura atual)

1. **[`docs/architecture/CURRENT_ARCHITECTURE.md`](docs/architecture/CURRENT_ARCHITECTURE.md)** —
   **a única referência da arquitetura atual.** Componentes, limites dos módulos, banco
   (dev vs produção), worker, scheduler, busca, IA, ingestão, observabilidade, deploy, e ainda
   os blocos **PLANNED**, **DEFERRED**, **KNOWN RISKS** e **HISTORICAL**. Cada afirmação tem
   evidência `arquivo:linha`; se divergir do código, o código está certo e o documento precisa
   de conserto.
2. **[`docs/architecture/ROADMAP.md`](docs/architecture/ROADMAP.md)** — o que está declarado
   como trabalho aberto (o plano do ciclo v1.1, os itens DEFERRED e os riscos conhecidos).
3. **[`docs/adr/`](docs/adr/)** — as decisões estruturais e o preço pago por elas
   (ADR-0001 banco, 0002 fila de jobs, 0003 busca, 0004 monolito modular, 0005 estratégia de IA).
4. **[`CLAUDE.md`](CLAUDE.md)** — comandos (setup, run, testes, lint, migrations) e convenções.
5. **[`docs/README.md`](docs/README.md)** — índice da documentação por categoria.

## Regras que não se negociam

- **Nunca** trate um plano antigo como backlog aberto. `BHUB_REFACTORING_PLAN.md`,
  `bhub-backend-python/ARCHITECTURE_REPORT.md`, `docs/ESTADO_ATUAL_PROJETO.md` e os guias de
  `docs/arquitetura/` descrevem ciclos **encerrados**: os checkboxes deles podem estar
  desmarcados mesmo com o trabalho feito. Antes de "implementar" algo dali, confira o código,
  as ADRs e `CURRENT_ARCHITECTURE.md`.
- **Produção é PostgreSQL 16** (ADR-0001). SQLite existe como compatibilidade de
  desenvolvimento e da suíte unitária — nunca como o banco de produção.
- **Jobs rodam em ARQ sobre Redis** (ADR-0002), com worker em processo separado.
  `asyncio.create_task` sobrevive apenas no executor inline de desenvolvimento
  (`ENABLE_ARQ=false`) e não é a estratégia de jobs.
- **Riscos conhecidos permanecem riscos** enquanto não houver task própria: não "conserte" de
  passagem os itens de KNOWN RISKS (`R-01`…`R-12` em `CURRENT_ARCHITECTURE.md` §13).
- Trabalho novo entra pelo plano do ciclo atual, não por reescrita silenciosa de documento
  histórico.

## Onde vive o quê

- Aplicação: `bhub-backend-python/` (FastAPI, Python 3.12+). **Todos os comandos de backend
  assumem esse diretório.**
- Documentação: `docs/` — índice em [`docs/README.md`](docs/README.md).
- Andamento do ciclo v1.1 (relatórios por task, com evidência):
  [`.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/`](.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/).

## Comandos essenciais

```bash
cd bhub-backend-python
pip install -r requirements-dev.txt     # ambiente de desenvolvimento
cp .env.example .env                    # depois edite .env
alembic upgrade head                    # aplica a cadeia de migrações
uvicorn app.main:app --reload            # servidor de desenvolvimento

pytest tests/ -q                        # suíte unitária (a de integração exige containers)
ruff check app tests && ruff format --check .
mypy app
```

Deploy de produção: `docker compose -f docker-compose.prod.yml up -d` **de dentro de
`bhub-backend-python/`** (é o único compose com PostgreSQL + Redis + `arq-worker`) —
procedimento operacional em [`docs/deploy/RUNBOOK.md`](docs/deploy/RUNBOOK.md).

Detalhes, variáveis de ambiente e convenções de código: [`CLAUDE.md`](CLAUDE.md).

---

<claude-mem-context>
# Memory Context

# claude-mem status

This project has no memory yet. The current session will seed it; subsequent sessions will receive auto-injected context for relevant past work.

Memory injection starts on your second session in a project.

`/learn-codebase` is available if the user wants to front-load the entire repo into memory in a single pass (~5 minutes on a typical repo, optional). Otherwise memory builds passively as work happens.

Live activity: http://localhost:37701
How it works: `/how-it-works`

This message disappears once the first observation lands.
</claude-mem-context>
