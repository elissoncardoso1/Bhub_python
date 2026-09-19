# ADR-0003 — Busca full-text em PostgreSQL (TSVECTOR + pg_trgm)

## Status

Aceito e implementado. Migração `008_postgres_fts` (2026-05-06); revalidado com PostgreSQL
16 real na Task 13 (`tests/integration/test_postgres_search.py`).

## Contexto

A busca do BHub é acadêmica e multilíngue: o acervo é majoritariamente em inglês, mas os
usuários pesquisam em português (e vice-versa, por causa da tradução automática). A
implementação original usava FTS5 do SQLite sobre tabela virtual com `content='articles'`,
o que atendia o desenvolvimento mas não oferecia ranking com pesos nem similaridade
aproximada — e o FTS5 não existe no PostgreSQL, para onde a produção estava indo
(ADR-0001). O acervo inclui ainda consultas com pontuação, DOI e operadores que não podem
virar erro 500 nem SQL executável.

A restrição de partida: a suíte unitária roda em SQLite e não podia perder a cobertura da
busca. Um segundo motor teria de coexistir com o primeiro.

## Decisão

**Produção usa full-text nativo do PostgreSQL**, com a coluna `articles.search_vector`
(`TSVECTOR`) e `pg_trgm` para similaridade. A migração `008_postgres_fts` cria a extensão,
a coluna, a função `articles_search_vector_update()`, o trigger `articles_search_vector_trigger`
(`BEFORE INSERT OR UPDATE`, `FOR EACH ROW`) e dois índices GIN:
`idx_articles_search_vector` sobre `search_vector` e `idx_articles_title_trgm` sobre
`articles.title gin_trgm_ops` (`alembic/versions/008_postgres_fts.py:29-71`). O mesmo
bloco é repetido de forma idempotente em `init_db()`
(`app/database.py:109-140`) para o caminho de banco criado por `create_all`.

A função de índice atribui pesos: `title` como `A` e `abstract` como `B`, **em português e
em inglês**, somando os quatro vetores
(`alembic/versions/008_postgres_fts.py:37-40`).

A consulta (`app/services/search_service.py:56-80`) usa `plainto_tsquery('portuguese', ...)`
(bind-param, nunca concatenação de string) e ordena por
`ts_rank_cd(Article.search_vector, ts_query)` com desempate por `publication_date DESC`,
filtrando por `is_published` e usando o operador `@@`.

`SearchService.search()` escolhe o motor pelo dialeto da sessão (`:22-24`): PostgreSQL usa
`_search_postgres_ids`; qualquer outro dialeto usa `search_fts5` e, se não houver
resultado, `search_like_fallback`. A sugestão (`get_suggestions`, `:247-270`) usa
`func.similarity(Article.title, query)` com `ilike '%query%'` no PostgreSQL.

O SQLite mantém a tabela virtual `articles_fts` e os triggers `articles_ai` / `articles_ad`
/ `articles_au` (`app/database.py:145-186`).

## Consequências

- Ranking real com pesos de campo, o que o FTS5 não dava, e similaridade aproximada para
  sugestões via `pg_trgm` — sem serviço de busca externo.
- O vetor é mantido por trigger do banco: qualquer escrita, incluso script fora do ORM,
  atualiza o índice. Não existe passo de reindexação a lembrar.
- **Negativo — duas implementações de busca coexistem.** O ramo PostgreSQL, o FTS5 e o
  fallback `LIKE` precisam ser mantidos em paralelo; o piso de cobertura roda só a suíte
  unitária (SQLite), então o ramo PostgreSQL só tem cobertura em
  `tests/integration/test_postgres_search.py`, que exige containers.
- **Negativo — o lado da consulta é sempre `portuguese`.** O índice carrega lexemas em
  português e inglês, mas a consulta é interpretada apenas com a configuração
  `portuguese` (`app/services/search_service.py:66`). Termos em inglês que dependam do stemming inglês
  não são normalizados da mesma forma que o índice — a busca funciona, o recall não é
  equivalente nas duas línguas.
- **Negativo — assimetria entre dialetos nas sugestões.** No ramo SQLite o resultado
  inclui nomes de categoria (`:294-298`); no ramo PostgreSQL as sugestões são só títulos.
- **Negativo — coluna `deferred` problemática em subquery.** `search_vector` é declarado
  `deferred=True` (`app/models/article.py:103-108`), o que **não** é honrado quando a
  entidade é envolvida em `.subquery()` (a query de contagem), então a coluna é
  selecionada e um banco atrasado em migração responde 500 em `/articles`. O sintoma e o
  conserto operacional (`alembic upgrade head`) estão em `CLAUDE.md` § Gotchas.
- **Negativo — o ranking não é idêntico entre os dialetos.** Qualquer teste de ranking
  escrito em SQLite não prova nada sobre o comportamento de produção; a cobertura real
  desse comportamento depende dos containers de integração.
- **Negativo — o teste de ordenação depende do plano do PostgreSQL.** Com
  `enable_sort=off` (HashAggregate) a query sem `ORDER BY` devolve a ordem esperada e o
  teste passa por acidente (N1 da Task 13). No plano default o mutante é pego.

## Alternativas consideradas

- **FTS5 em produção (manter SQLite).** Inviável depois da ADR-0001: FTS5 não existe no
  PostgreSQL e o banco é único.
- **Serviço externo de busca (Elasticsearch/OpenSearch, Meilisearch, Typesense).** Rejeitada:
  mais um componente para operar e sincronizar, num projeto de um servidor só; o
  levantamento comparativo está em `docs/rss/rss_research.md`.
- **`tsvector` sem `pg_trgm`.** Funcionaria para full-text, mas perderia a similaridade
  das sugestões e o índice sobre `title` para `ilipe`/`ilike` — as duas coisas foram
  pedidas juntas.
- **Coluna gerada (`GENERATED ALWAYS AS ... STORED`) em vez de trigger.** Não adotada:
  a expressão de `to_tsvector` com pesos e duas configurações de idioma não era imutável
  de forma confiável no momento da migração; o trigger é explícito e já reescreve os
  registros existentes no `UPDATE` da migração.
- **Busca vetorial/semântica com embeddings.** Continua como PLANNED, sem implementação —
  ver `CURRENT_ARCHITECTURE.md` § PLANNED. Não substitui o full-text lexical, que é o que
  existe hoje.
