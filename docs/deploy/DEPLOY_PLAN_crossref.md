# DEPLOY PLAN — Ingestão de periódicos via Crossref (ADR-0007)

**Data do plano:** 2026-09-26
**Branch:** `feat/journal-feeds-crossref` @ `4bffde5` (2 commits sobre `v1.1`/`81612b3`)
**Alvo:** srv988042 — `/var/www/bhub.online`
**Imagem atual em produção:** `bhub-backend-python-backend:latest` = `sha256:ee7d9854dd87` = **v1.1** (`81612b3`)
**Revisão de banco atual:** `009_feed_http_cache` → **nova:** `010_feed_journal_source`
**Downtime previsto:** ~30-60s (recreate de `backend` + `arq-worker`)

---

## 1. O que este deploy resolve

Sete dos onze feeds de periódicos estão sem coletar desde ~agosto/2026, por anti-bot das
editoras (Wiley/T&F: HTTP 403; Springer: HTTP 200 com HTML de challenge). O ADR-0006 fez a
falha aparecer; este deploy troca a fonte pelo **Crossref**, que é público e indexado por
ISSN.

Inclui também o commit `0ae4dfb` (ADR-0006), que **não está em produção hoje** — sem ele a
falha silenciosa da Springer continuaria invisível.

| Item | Origem |
| --- | --- |
| D1 — HTTP 200 com corpo não-RSS deixa de contar como sucesso | `0ae4dfb` (ADR-0006) |
| Adaptador Crossref + ingestão dos periódicos | `4bffde5` (ADR-0007) |
| D2 — `max_errors` passa a desativar, com sonda de recuperação íntegra | `4bffde5` |
| D3 — seed idempotente + URL OJS corrigida da Perspectivas | `4bffde5` |

**NÃO altera layout, rotas públicas nem templates.** A única mudança visível ao público é a
composição da lista de fontes em `/api/v1/feeds` (feeds desativados somem — ver §5).

---

## 2. Pré-requisitos e ambiente

O host roda o **backend em container**, não em venv. Comandos de aplicação são executados via
`docker run` com a **imagem recém-construída**, porque é ela que contém `alembic/versions/010`
e os scripts novos. Nunca use a imagem antiga para migrar: ela não conhece a 010.

Variáveis de ambiente de produção são lidas do arquivo `.env` no diretório do compose
(`/var/www/bhub.online/Bhub_python/bhub-backend-python/.env`) — **não** passe `-e` para
`docker compose`.

As settings novas do Crossref (`CROSSREF_MAILTO`, `CROSSREF_ROWS`, `CROSSREF_MAX_PAGES`,
etc.) têm **default em `app/config.py`**, então o `.env` **não precisa ser alterado**. O
`mailto` default é `pontobhv@proton.me` (o mesmo do rodapé do site) — confirme que é um
endereço monitorado, já que o Crossref o usa para avisar sobre cota.

---

## 3. Riscos

### R1 — REGRESSÃO DE RELEASE (crítico) — o maior risco deste deploy

A árvore de produção `/var/www/bhub.online/Bhub_python` está em **`main` = `c7f3598`**, que
é 99 commits atrás e **divergente** de `v1.1`/`81612b3`, além de ter 6 arquivos sujos (UI).
`git diff c7f3598 81612b3 -- bhub-backend-python/app` mostra **85 arquivos** e ~2.600 linhas
de mudança.

**Consequência:** construir a imagem a partir daquela árvore (`docker compose build`)
**regride a v1.1 inteira** — PDF service, busca FTS, OpenGraph, classificação, ARQ, templates.
Seria um incidente grave, silencioso e amplo.

`docker-compose.prod.yml` e `Dockerfile` são **idênticos** entre as duas árvores (verificado),
então o compose pode ser executado de qualquer uma — mas o **contexto de build** importa.

**Mitigação:** construir **exclusivamente** a partir de `hotfix-feed-validation` (que está em
`v1.1` + os 2 commits), e rodar o `compose up` **sem `--build`**. Passo 4 abaixo. O
`--no-build` é obrigatório; `--build` aqui é o erro fatal do deploy.

### R2 — `max_errors` desativa feeds de notícias (esperado, mas novo)

Com o D2, feeds com falha **permanente** e `error_count >= max_errors` passam a ser
desativados na sua próxima tentativa. Levantamento em produção (2026-09-26):

| id | Feed | `error_count` | Último erro | Deve desativar? |
| --- | --- | --- | --- | --- |
| 12 | Brighter Strides ABA | 16 | HTTP 403 | **Sim** |
| 26 | Blog ABAEDU | 16 | HTTP 404 | **Sim** |
| 3 | Applied Behavior Analysis Edu | 11 | HTTP 410 | **Sim** |
| 2 | I Love ABA! | 6 | HTTP 403 | **Sim** |
| 23 | WayABA | 5 | Erro de rede (DNS) | Não — transitório |
| 1 | ABAI Science Blog | 5 | Erro de rede (DNS) | Não — transitório |

Só os **4 primeiros** desativam: erro de rede é `TRANSIENT_ERROR` e **não** incrementa
`error_count` nem desativa (correto — indisponibilidade de rede não é defeito da fonte).

Não é imediato: `needs_sync` só libera um feed com erros após
`RECOVERY_PROBE_INTERVAL_DAYS` (7 dias) desde o último sync. A desativação acontece **ao
longo de até 7 dias**, conforme cada feed é sondado. Os ids 26 e 3 (404/410) passam antes
pela **redescoberta automática** de feed e podem se recuperar sozinhos.

### R3 — Não existe imagem de rollback (crítico)

`backups/preflight_20260922_175222/ROLLBACK_PLAN.md` referencia a tag
`bhub-backend-python-backend:rollback-c7f3598`, mas `docker images` mostra que **ela não
existe mais** — só `latest`. Sem um artefato de rollback, uma falha não tem volta verificada.

**Mitigação:** passo 1 cria `rollback-v1.1-ee7d9854` a partir da imagem em execução, **antes**
de qualquer mudança.

### R4 — Restart do backend durante um sync em andamento

O job `sync_feeds` roda a cada hora (minuto 0, `America/Sao_Paulo`) atrás de um lock
distribuído de TTL 30 min. Recriar o container no meio de um sync interrompe o job; o lock
fica até expirar (30 min), durante os quais o job não roda — sem dano, mas sem sync.

**Mitigação:** fazer o deploy fora do minuto 0 (janela recomendada: minuto 5-50), conferir
`SELECT * FROM scheduler_locks` antes e depois.

### R5 — `scripts/vps/backup.sh` está desatualizado (não usar)

O script aponta para `PROJECT_DIR=/var/www/bhub` (caminho inexistente) e copia arquivo
**SQLite** — o banco de produção é **PostgreSQL**. Rodá-lo não faz backup algum. O RUNBOOK
já registra que `scripts.backup_db`/`restore_db` são **somente dev/SQLite**.

**Mitigação:** usar `pg_dump` diretamente (passo 2). Não confie em `backup.sh`.

### R6 — Escopo do gate de tipos mudou

`.github/workflows/ci.yml` passou `EXPECTED_SOURCE_FILES` de **105 → 106** (o arquivo novo
`app/services/crossref_source.py`). O orçamento de erros **não** subiu: **127 antes e depois**.
O gate falha se o escopo divergir, então a mudança é obrigatória e está justificada no
próprio arquivo, como o step exige.

### R7 — Gates de CI medidos localmente (todos verdes)

| Gate | Resultado |
| --- | --- |
| `ruff check app tests` | All checks passed |
| `ruff format --check .` | 199 files already formatted |
| `mypy app --config-file pyproject.ratchet.toml` | 127 errors / 106 files (orçamento 127) |
| `mypy app` (strict, bloqueante) | Success: no issues found in 106 files |
| `pytest tests/` | **327 passed** |
| Coverage floor 59,19% | **60,82%** (subiu com os testes novos) |
| Migração 010 em PostgreSQL real | upgrade → downgrade → upgrade OK |
| E2E Crossref (API real + banco real) | 37 artigos, 2º sync sem duplicatas |

> A suíte de **integração** (`tests/integration`, marcada `integration`) sobe Postgres/Redis
> próprios e não foi executada aqui. Ela é um step do CI e roda `alembic upgrade head` em
> banco vazio. Se o pipeline for acionado, ele cobre isso.

---

## 4. Procedimento

Todos os comandos assumem `SRC=/var/www/bhub.online/hotfix-feed-validation` e
`PROD=/var/www/bhub.online/Bhub_python/bhub-backend-python`.

### Passo 0 — Pré-voo

```bash
cd $SRC && git log --oneline -1        # deve ser 4bffde5
git status --porcelain | head          # deve estar vazio (árvore limpa)
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT version_num FROM alembic_version;"   # 009_feed_http_cache
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT count(*) FROM scheduler_locks;"      # 0 = sem sync em andamento
curl -s http://127.0.0.1:8000/health   # healthy
date +%M                               # NÃO iniciar com minuto próximo de 00 (ver R4)
```

### Passo 1 — Ponto de rollback (R3)

```bash
docker image inspect bhub-backend-python-backend:latest \
  --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
# Esperado: sha256:ee7d9854... 81612b3...

docker tag bhub-backend-python-backend:latest bhub-backend-python-backend:rollback-v1.1-ee7d9854
docker images --format '{{.Repository}}:{{.Tag}}' | grep rollback-v1.1   # confirmar
```

### Passo 2 — Backup do banco (R5)

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
docker exec bhub-postgres pg_dump -U bhub -d bhub -Fc > /var/www/bhub.online/backups/bhub_${STAMP}_pre-crossref.dump
sha256sum /var/www/bhub.online/backups/bhub_${STAMP}_pre-crossref.dump
# Verificar que o dump é legível (não basta ter tamanho > 0):
docker cp /var/www/bhub.online/backups/bhub_${STAMP}_pre-crossref.dump bhub-postgres:/tmp/check.dump
docker exec bhub-postgres pg_restore --list /tmp/check.dump | head
docker exec bhub-postgres rm -f /tmp/check.dump
```

**Não prossiga se a listagem falhar.** Guarde o `STAMP` — o rollback usa este arquivo.

### Passo 3 — Build da imagem (R1)

Build a partir de `$SRC`, **nunca** de `$PROD`. O build leva **~10 min** (llama-cpp-python
compila do fonte).

```bash
cd $SRC/bhub-backend-python
docker build -t bhub-backend-python-backend:latest . 2>&1 | tee /var/www/bhub.online/backups/build-adr0007.log | tail -20
echo "BUILD_EXIT=${PIPESTATUS[0]}"
```

Conferir que a imagem nova é **diferente** da v1.1 e carrega a revisão certa:

```bash
docker image inspect bhub-backend-python-backend:latest --format '{{.Id}}'
docker run --rm --entrypoint sh bhub-backend-python-backend:latest \
  -c "ls alembic/versions/ | grep 010; python -c 'import app.services.crossref_source; print(\"crossref ok\")'"
# Deve imprimir 010_feed_journal_source.py e "crossref ok".
# Se NÃO imprimir, o build pegou contexto errado — NÃO continue.
```

### Passo 4 — Aplicar a migração 010

Com a aplicação ainda em v1.1 (aditivo; código antigo ignora as colunas novas). O container
`db` está publicado apenas na rede interna, então rode pela rede do compose.

A `DATABASE_URL` é **lida do container em execução** — assim a senha não entra neste
documento nem no histórico do git (`docs/` é versionado). O container `bhub-backend` já está
no ar com a variável correta:

```bash
cd $PROD
DBURL=$(docker exec bhub-backend printenv DATABASE_URL)
test -n "$DBURL" || { echo "DATABASE_URL vazia — abortar"; exit 1; }

docker compose -f docker-compose.prod.yml run --rm --no-deps \
  -e DATABASE_URL="$DBURL" backend alembic upgrade head
```

> **Não** rode `alembic` a partir de `$SRC` sem essa variável: o default é SQLite e criaria um
> banco local — a migração falharia no SQLite por causa do `ENUM` nativo.
>
> Se preferir não passar pela aplicação, use `grep '^DATABASE_URL' .env` (o `.env` de
> produção é a fonte, não versionado). **Nunca** cole o valor em tickets, chat ou docs.

Verificar:

```bash
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT version_num FROM alembic_version;"        # 010_feed_journal_source
docker exec bhub-postgres psql -U bhub -d bhub -c "\d feeds" | grep -E 'journal_source|issn|deactivated_by_errors'
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT count(*) FROM feeds WHERE journal_source='RSS';"   # 40 (default aplicado)
```

### Passo 5 — Recriar os serviços

`--no-build` é **obrigatório** (R1): a imagem correta já foi construída no passo 3.

```bash
cd $PROD
docker compose -f docker-compose.prod.yml up -d --no-build --force-recreate backend arq-worker
sleep 15
curl -s http://127.0.0.1:8000/health; echo
docker logs --tail 30 bhub-backend
```

### Passo 6 — Conversão dos periódicos

Dry-run primeiro; **confira a saída antes de aplicar**.

```bash
docker exec bhub-backend python -m scripts.migrate_journal_feeds_to_crossref
```

Saída esperada: 7 periódicos com `migrar p/ Crossref`, 1 `desativar` (OBM Network News) e
**nenhum** `NÃO ENCONTRADO` (se houver, o nome no banco diverge do script — investigue antes).

```bash
docker exec bhub-backend python -m scripts.migrate_journal_feeds_to_crossref --apply
```

### Passo 7 — Validar a fonte externa

```bash
docker exec bhub-backend python -m scripts.validate_journal_issn --all
```

**Leia os títulos devolvidos, um por um.** Validar só prova que o ISSN existe: em teste,
`9999-9999` retornou sucesso com o título *"Space Resolver 16"*. Os 21 ISSNs foram conferidos
manualmente antes deste plano, mas confirme novamente na VPS — é a última rede de proteção
contra um ISSN trocado.

---

## 5. Critérios de aceite

```bash
# 1. Estado de cada periódico: via de ingestão, ISSN, erros
docker exec bhub-postgres psql -U bhub -d bhub -c "
SELECT id, name, journal_source, issn, is_active, error_count, last_error
FROM feeds WHERE journal_name IS NOT NULL ORDER BY name;"
```

| Critério | Esperado |
| --- | --- |
| Periódicos migrados | 7 com `journal_source=CROSSREF` e `issn` preenchido |
| Erros dos migrados | `error_count=0` e `last_error=NULL` (a migração zera a dívida da fonte antiga) |
| OBM Network News | `is_active=false` |
| Feeds de notícias | Nenhum desativado **imediatamente** (desativação é gradual — R2) |

```bash
# 2. Sync real de um periódico (id 33 = JABA)
docker exec bhub-backend python -c "
import asyncio
from app.database import get_session_context
from app.services import FeedAggregatorService
async def main():
    async with get_session_context() as db:
        svc = FeedAggregatorService(db)
        try:
            r = await svc.sync_feed(33)
            print(r.model_dump())
        finally:
            await svc.close()
asyncio.run(main())"
```

Esperado: `success=True` com `new_articles>0` (JABA deposita regularmente) e **nenhuma**
requisição a `onlinelibrary.wiley.com` nos logs.

```bash
# 3. Artigos novos por periódico (últimos 30 dias)
docker exec bhub-postgres psql -U bhub -d bhub -c "
SELECT f.id, f.name, count(a.id) AS artigos, max(a.publication_date)::date AS ultimo
FROM feeds f LEFT JOIN articles a ON a.feed_id=f.id
WHERE f.journal_name IS NOT NULL GROUP BY f.id, f.name ORDER BY 2 DESC NULLS LAST;"
```

Antes deste deploy, os periódicos da Springer pararam em **2026-08-04**. Esperado: artigos
com data de setembro/2026 para BAP, PoBS, TAVB, BSI, JABA, JEAB e JOBM.

```bash
# 4. Sem duplicatas por DOI (republicações Early View)
docker exec bhub-postgres psql -U bhub -d bhub -c "
SELECT lower(doi), count(*) FROM articles WHERE doi IS NOT NULL
GROUP BY 1 HAVING count(*) > 1 LIMIT 10;"     # deve ser vazio
```

```bash
# 5. Scheduler ativo e sem lock preso (R4)
docker exec bhub-backend python -c "
from app.jobs import get_scheduler_status; import json; print(json.dumps(get_scheduler_status(), indent=2))"
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT lock_name, expires_at FROM scheduler_locks;"
```

**Rollback se:** qualquer periódico migrado com `error_count>0` persistente, duplicatas por
DOI, `/health` não saudável, ou logs com traceback repetido no `crossref_source`.

---

## 6. Rollback

### Aplicação (rápido, ~30s)

O schema novo é **aditivo** e a v1.1 o ignora (SQLAlchemy não seleciona colunas que não
conhece). Não é necessário reverter a migração para voltar a aplicação.

```bash
docker tag bhub-backend-python-backend:rollback-v1.1-ee7d9854 bhub-backend-python-backend:latest
cd /var/www/bhub.online/Bhub_python/bhub-backend-python
docker compose -f docker-compose.prod.yml up -d --no-build --force-recreate backend arq-worker
sleep 15 && curl -s http://127.0.0.1:8000/health; echo
```

> Efeito colateral: a v1.1 **não tem o D1**, então os feeds da Springer voltam a marcar
> sucesso falso. Aceitável por curto prazo (é o estado atual), mas o motivo do rollback deve
> ser investigado antes de reintentar.

### Banco (somente se dados incorretos)

```bash
docker cp /var/www/bhub.online/backups/bhub_${STAMP}_pre-crossref.dump bhub-postgres:/tmp/
docker exec -i bhub-postgres pg_restore -U bhub -d bhub --clean --if-exists --no-owner /tmp/bhub_${STAMP}_pre-crossref.dump
docker exec bhub-postgres psql -U bhub -d bhub -c "SELECT version_num FROM alembic_version;"   # volta a 009
```

`--clean --if-exists` derruba e recria os objetos: **perde artigos ingeridos após o backup**.
Use só se houver dado incorreto, não como parte do rollback normal.

### Migração (reversível, sem restore)

```bash
cd $PROD
DBURL=$(docker exec bhub-backend printenv DATABASE_URL)
docker compose -f docker-compose.prod.yml run --rm --no-deps \
  -e DATABASE_URL="$DBURL" backend alembic downgrade 009_feed_http_cache
```

Validado em PostgreSQL real (upgrade → downgrade → upgrade). Remove as 3 colunas e o enum
`feedjournalsource`.

---

## 7. Pós-deploy

- [ ] Registrar o deploy em `backups/DEPLOY_RECORD_*.md` (SHA, image ID, revisão de banco, veredito).
- [ ] Acompanhar `error_count` dos periódicos por **7 dias**. Um ISSN errado só aparece como
      "ISSN não encontrado" no primeiro sync real.
- [ ] Confirmar que os 4 feeds de notícias com falha permanente (ids 12, 26, 3, 2) foram
      desativados **ou** recuperados pela redescoberta — os dois resultados são aceitáveis, mas
      a curadoria decide se devem voltar (`UPDATE feeds SET is_active=true, deactivated_by_errors=false WHERE id=...`).
- [ ] Decidir sobre a **ampliação** do ADR-0007 (REBAC, RBTCC e 12 internacionais): a lista de
      candidatos com ISSNs já validados está em `scripts/validate_journal_issn.py`.
- [ ] Integrar o branch na linha principal (o `Bhub_python` está 99 commits à frente; a
      reconciliação é trabalho separado e **é o que destrava builds a partir daquela árvore** — R1).

---

## 8. Resumo executável

```bash
SRC=/var/www/bhub.online/hotfix-feed-validation
PROD=/var/www/bhub.online/Bhub_python/bhub-backend-python
STAMP=$(date +%Y%m%d_%H%M%S)

# 1. rollback point
docker tag bhub-backend-python-backend:latest bhub-backend-python-backend:rollback-v1.1-ee7d9854

# 2. backup
docker exec bhub-postgres pg_dump -U bhub -d bhub -Fc > /var/www/bhub.online/backups/bhub_${STAMP}_pre-crossref.dump

# 3. build (a partir de $SRC — NUNCA de $PROD)
cd $SRC/bhub-backend-python && docker build -t bhub-backend-python-backend:latest .

# 4. migração (DATABASE_URL vem do container, não deste documento)
DBURL=$(docker exec bhub-backend printenv DATABASE_URL)
cd $PROD && docker compose -f docker-compose.prod.yml run --rm --no-deps -e DATABASE_URL="$DBURL" backend alembic upgrade head

# 5. recreate
docker compose -f docker-compose.prod.yml up -d --no-build --force-recreate backend arq-worker

# 6. conversão
docker exec bhub-backend python -m scripts.migrate_journal_feeds_to_crossref          # dry-run
docker exec bhub-backend python -m scripts.migrate_journal_feeds_to_crossref --apply

# 7. validar
docker exec bhub-backend python -m scripts.validate_journal_issn --all
curl -s http://127.0.0.1:8000/health; echo
```

**Os três erros que este plano existe para evitar:** (1) `docker compose build` a partir de
`$PROD` — regride a v1.1 em 85 arquivos; (2) deploy sem ponto de rollback — a tag referenciada
no plano anterior não existe mais; (3) confiar em `scripts/vps/backup.sh` — é SQLite e caminho
inexistente.
