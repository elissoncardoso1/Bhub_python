# ADRs — BHub Backend

Registro das decisões arquiteturais que sustentam a arquitetura atual
([`../architecture/CURRENT_ARCHITECTURE.md`](../architecture/CURRENT_ARCHITECTURE.md)).

Cada ADR tem exatamente cinco seções, como títulos de segundo nível e nesta ordem:
`## Status`, `## Contexto`, `## Decisão`, `## Consequências` e `## Alternativas
consideradas`. Não são tutoriais: registram o motivo da decisão e o preço pago por ela —
inclusive as consequências negativas.

| ADR | Decisão | Status |
|---|---|---|
| [0001](0001-postgresql-producao.md) | PostgreSQL como banco de produção (SQLite só em dev/testes) | Aceito e implementado |
| [0002](0002-arq-fila-de-jobs.md) | ARQ sobre Redis como estratégia de jobs; inline só como fallback de dev | Aceito e implementado |
| [0003](0003-busca-full-text.md) | Busca full-text em PostgreSQL com `TSVECTOR` + `pg_trgm` | Aceito e implementado |
| [0004](0004-monolito-modular.md) | Monolito modular com `Protocol`s em `app/interfaces/` e DI por `Depends` | Aceito e implementado |
| [0005](0005-estrategia-de-ia.md) | IA multi-provedor com degradação para ML local e heurística | Aceito e implementado |

**Como escrever um ADR novo:** numere em sequência (`0006-...`), mantenha as cinco seções
nessa ordem e cite `arquivo:linha` do código que sustenta a decisão. Uma decisão que muda
não se reescreve: cria-se um ADR novo e o antigo passa a **Substituído por ADR-NNNN**.
