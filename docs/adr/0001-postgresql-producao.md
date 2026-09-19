# ADR-0001 — PostgreSQL como banco de produção

## Status

Aceito e implementado. Em produção desde a migração `008_postgres_fts` (2026-05-06);
revalidado com PostgreSQL 16 real na Task 12 (`tests/integration/test_migrations.py`).

## Contexto

O BHub nasceu sobre SQLite com FTS5. Com três processos escrevendo no mesmo banco — o
app web (`backend`), o worker ARQ (`arq-worker`) e o job horário de sincronização de feeds
disparado pelo scheduler dentro do `backend` —, o modelo single-writer do SQLite passa a
ser o gargalo: a ingestão de feeds, o tracking de analytics e o processamento de PDFs
competem pelo mesmo lock de escrita. Além disso, a busca full-text precisava de ranking
multilíngue, e o `pg_trgm`/`TSVECTOR` do PostgreSQL oferece isso sem um serviço externo.

O custo de troca era conhecido: a suíte unitária depende de SQLite em memória
(`tests/conftest.py:19`) e vários testes dependem do comportamento do dialeto. O repositório
não podia perder a compatibilidade de desenvolvimento.

## Decisão

Produção roda **PostgreSQL 16** (`postgres:16-alpine`), com o driver assíncrono `asyncpg`.
O compose de produção injeta `DATABASE_URL=postgresql+asyncpg://bhub:bhub@db:5432/bhub`
nos dois processos que falam com o banco (`bhub-backend-python/docker-compose.prod.yml:32`
e `:85`). O engine cresce para um pool real (`pool_size=20`, `max_overflow=10`,
`pool_pre_ping=True`, `pool_recycle=3600`) quando a URL é PostgreSQL
(`app/database.py:27-33`).

O SQLite permanece como banco **de desenvolvimento e de testes unitários**: o default de
`settings.database_url` continua `sqlite+aiosqlite:///./bhub.db` (`app/config.py:59`) e a
suíte unitária roda em `:memory:`. O schema suporta os dois dialetos por `with_variant`
(`app/models/article.py:103-108`) e `init_db()` bifurca por dialeto (`app/database.py:109-186`).
A cadeia de migrações é a mesma para os dois: `alembic/env.py:40` sobrescreve a URL do
`alembic.ini` com a variável de ambiente do processo.

A busca full-text deixou de ser FTS5 em produção — ver ADR-0003.

## Consequências

- Escrita concorrente real, com pool de conexões, `pool_pre_ping` e `pool_recycle` no lugar
  do lock de arquivo do SQLite.
- Consistência de dialeto virou responsabilidade do código: `init_db` e a migração 008
  tratam `pg_trgm`/`TSVECTOR`/trigger **apenas** no ramo PostgreSQL, e o ramo SQLite
  mantém a tabela virtual FTS5 e os três triggers próprios. Duas implementações de busca
  coexistem e ambas precisam ser mantidas.
- A migração é operacionalmente sensível: um banco criado por `Base.metadata.create_all`
  tem as tabelas mas **nenhuma** linha em `alembic_version`, e `alembic upgrade head`
  falha nele. O procedimento de `stamp` e o drift medido de `create_all` contra a cadeia
  de migrações estão documentados em `docs/deploy/RUNBOOK.md` (seção "Banco que já existe
  e não tem `alembic_version`") — 34 definições de coluna e 6 objetos de índice divergem,
  em 8 tabelas.
- A URL efetiva **não é determinável pelo repositório**: quem decide é o `.env` da VPS
  (não versionado). Dois arquivos do próprio repositório ainda fixam SQLite
  (`config/env.production.template:29`, `scripts/vps/deploy.sh:96`) e o
  `docker-compose.prod.yml` da raiz também (`:31`) — divergência registrada, não corrigida
  nesta task porque exige tocar config/scripts/compose.
- Perda conhecida: a suíte unitária não exercita o caminho PostgreSQL. É por isso que
  `tests/integration/` existe e roda contra containers reais.

## Alternativas consideradas

- **Manter SQLite em produção com WAL e `busy_timeout`.** Rejeitada: não resolve
  multi-writer entre processos e não oferece o ranking de busca necessário; a própria
  revisão de arquitetura apontava o lock de escrita como gargalo (MÉDIO-ALTO).
- **SQLite para o app e PostgreSQL só para busca.** Rejeitada: dois bancos com o mesmo
  dado exigiriam sincronização, e o problema era justamente a escrita concorrente.
- **Remover o SQLite do repositório de vez.** Rejeitada nesta rodada: quebraria a suíte
  unitária inteira (que roda em `:memory:`) e o piso de cobertura, sem ganho direto para a
  confiabilidade de produção. O plano v1.1 diz explicitamente para não remover a
  compatibilidade de dev/testes sem decisão explícita.
- **MySQL/MariaDB.** Não avaliada em profundidade: não oferece `pg_trgm`/`TSVECTOR` com o
  mesmo custo de adoção, e o `asyncpg` era o caminho já mapeado pelo relatório de
  arquitetura e pelo plano de refatoração.
