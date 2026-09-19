# Runbook BHUB - Procedimentos Operacionais

**Versão**: 1.0.0  
**Data**: Janeiro 2025

> **Escopo:** o banco de **produção** é PostgreSQL 16 (`db`, `postgres:16-alpine`) e os
> comandos de operação abaixo usam `docker-compose exec db psql ...`. Os helpers
> `scripts/backup_db.py` / `scripts/restore_db.py` operam sobre **arquivo SQLite** e valem
> apenas para o banco de desenvolvimento (`DATABASE_URL=sqlite+aiosqlite:///./bhub.db`).
> Arquitetura atual: `docs/architecture/CURRENT_ARCHITECTURE.md`.

---

## 📋 Índice

1. [Backup e Restore](#backup-e-restore)
2. [Incidentes Comuns](#incidentes-comuns)
3. [Verificações de Saúde](#verificações-de-saúde)
4. [Manutenção](#manutenção)
5. [Troubleshooting](#troubleshooting)

---

## 💾 Backup e Restore

### Backup Automático

O backup automático é configurado via cron ou systemd timer (ver `DEPLOY_STAGING.md`).

**Localização dos backups**: `backups/bhub_backup_YYYYMMDD_HHMMSS.db`

> **Atenção (PostgreSQL):** `scripts/vps/backup.sh` copia um **arquivo** (`bhub.db`) — num
> deploy com PostgreSQL a produção não está nesse arquivo, então o backup automático não
> cobre o banco de produção. O backup do banco é `pg_dump`/`pg_dumpall` contra o serviço
> `db`; ver a seção "Verificar Integridade" para os comandos de leitura.

### Backup Manual (SQLite — apenas desenvolvimento)

Os comandos abaixo operam sobre **arquivo SQLite**; não os use contra o serviço `db`:

```bash
# Dentro do container
docker-compose exec backend python -m scripts.backup_db

# Com opções
docker-compose exec backend python -m scripts.backup_db \
  --backup-dir /app/backups \
  --retention-days 30
```

Para o banco de **produção** (PostgreSQL):

```bash
docker-compose exec db pg_dump -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -Fc -f /tmp/bhub_YYYYMMDD_HHMMSS.dump
docker cp "$(docker-compose ps -q db):/tmp/bhub_YYYYMMDD_HHMMSS.dump" backups/
```

### Restore

Backups **SQLite** (desenvolvimento) via `scripts.restore_db`:

```bash
# Listar backups disponíveis
docker-compose exec backend python -m scripts.restore_db --list

# Restaurar backup específico
docker-compose exec backend python -m scripts.restore_db \
  backups/bhub_backup_20250115_020000.db

# Restaurar sem criar backup do banco atual (NÃO RECOMENDADO)
docker-compose exec backend python -m scripts.restore_db \
  backups/bhub_backup_20250115_020000.db \
  --no-backup
```

Backup **PostgreSQL** (produção), restaurado no serviço `db`:

```bash
docker-compose exec -T db pg_restore -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  --clean --if-exists < backups/bhub_YYYYMMDD_HHMMSS.dump
```

### Verificar Integridade

O banco de **produção** é PostgreSQL: a integridade se verifica no servidor, não por
arquivo.

```bash
# Banco atual (PostgreSQL) — conectividade e sanidade do catálogo
docker-compose exec db pg_isready -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}"
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT count(*) AS tabelas FROM information_schema.tables WHERE table_schema = 'public';" \
  -c "SELECT version_num FROM alembic_version;"

# Backup lógico (formato próprio do PostgreSQL). O dump vive no host, em `backups/` (ao lado do
# compose, onde o `docker cp` acima grava); o serviço `db` só monta `postgres_data`, então copie o
# dump para dentro dele antes de ler o índice.
docker cp backups/bhub_YYYYMMDD_HHMMSS.dump "$(docker-compose ps -q db):/tmp/"
docker-compose exec db pg_restore --list /tmp/bhub_YYYYMMDD_HHMMSS.dump | head
```

Os scripts `scripts.backup_db` / `scripts.restore_db` operam sobre **arquivo SQLite** e
servem apenas ao banco de desenvolvimento (`DATABASE_URL=sqlite+aiosqlite:///./bhub.db`).
Não os use contra produção.

---

## 🚨 Incidentes Comuns

### 1. Aplicação Fora do Ar

**Sintomas**: Health check falha, site não responde

**Diagnóstico**:
```bash
# Verificar status do container
docker-compose ps

# Verificar logs
docker-compose logs --tail=100 backend

# Verificar recursos
docker stats bhub-backend
```

**Solução**:
```bash
# Tentar restart
docker-compose restart backend

# Se não funcionar, rebuild
docker-compose down
docker-compose up -d --build

# Verificar variáveis de ambiente
docker-compose exec backend env | grep -E "(SECRET_KEY|DATABASE_URL)"
```

### 2. Banco de Dados Corrompido

**Sintomas**: Erros de banco de dados, integridade falha, conexões travadas

> Os comandos abaixo assumem PostgreSQL (o banco de produção). Para o banco **de
> desenvolvimento** em SQLite, o equivalente é `sqlite3 bhub.db 'PRAGMA integrity_check;'`.

**Diagnóstico**:
```bash
# Verificar integridade (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT pg_is_in_recovery();" -c "SELECT 1;"

# Verificar locks (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT pid, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE datname = current_database();"
```

**Solução**:
```bash
# 1. Parar aplicação
docker-compose down

# 2. Restaurar o último backup do PostgreSQL (banco parado)
docker-compose up -d db
docker-compose exec -T db pg_restore -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  --clean --if-exists < backups/bhub_YYYYMMDD_HHMMSS.dump

# 3. Verificar integridade (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT count(*) FROM articles;" -c "SELECT version_num FROM alembic_version;"

# 4. Reiniciar aplicação
docker-compose up -d
```

### 3. Scheduler Não Executa

**Sintomas**: Feeds não sincronizam, jobs não rodam

**Diagnóstico**:
```bash
# Verificar se scheduler está rodando
docker-compose exec backend python -c "
from app.jobs import get_scheduler_status
import json
print(json.dumps(get_scheduler_status(), indent=2))
"

# Verificar locks
docker-compose exec backend python -c "
from app.database import get_session_context
from app.models import SchedulerLock
from sqlalchemy import select
import asyncio
async def check():
    async with get_session_context() as db:
        result = await db.execute(select(SchedulerLock))
        locks = result.scalars().all()
        for lock in locks:
            print(f'{lock.lock_name}: {lock.instance_id} (expira: {lock.expires_at})')
asyncio.run(check())
"
```

**Solução**:
```bash
# Se lock expirado, limpar manualmente (CUIDADO!)
docker-compose exec backend python -c "
from app.database import get_session_context
from app.models import SchedulerLock
from sqlalchemy import delete, select
from datetime import datetime
import asyncio
async def cleanup():
    async with get_session_context() as db:
        now = datetime.utcnow()
        result = await db.execute(
            delete(SchedulerLock).where(SchedulerLock.expires_at < now)
        )
        await db.commit()
        print(f'Locks expirados removidos: {result.rowcount}')
asyncio.run(cleanup())
"

# Reiniciar scheduler
docker-compose restart backend
```

### 4. Rate Limit Excessivo

**Sintomas**: Muitas requisições retornam 429

**Diagnóstico**:
```bash
# Verificar logs de rate limit
docker-compose logs backend | grep -i "rate limit"

# Verificar configuração
docker-compose exec backend python -c "
from app.config import settings
print(f'Rate limit: {settings.rate_limit_requests}/{settings.rate_limit_period}s')
"
```

**Solução**:
- Ajustar limites em `.env` (se necessário)
- Verificar se há ataque/abuso
- Considerar aumentar limites temporariamente

### 5. Disco Cheio

**Sintomas**: Erros de escrita, backups falham

**Diagnóstico**:
```bash
# Verificar espaço
df -h

# Verificar tamanho do banco (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS banco;"

# Verificar tamanho dos backups (no host: `backups/` fica ao lado do compose, não dentro do
# container `db`, que só monta `postgres_data`)
du -sh backups/

# Verificar tamanho dos logs
docker-compose exec backend du -sh logs/
```

**Solução**:
```bash
# Limpar backups antigos
docker-compose exec backend python -m scripts.backup_db --retention-days 7

# Limpar logs antigos (se configurado)
docker-compose exec backend find logs/ -name "*.log" -mtime +30 -delete

# Limpar uploads antigos (se necessário)
docker-compose exec backend find uploads/ -type f -mtime +90 -delete
```

---

## 🔍 Verificações de Saúde

### Verificação Diária

```bash
#!/bin/bash
# health-check-daily.sh

echo "=== Verificação Diária BHUB ==="

# Health check
echo "1. Health check:"
curl -f http://localhost:8000/health || echo "FALHOU"

# Status do container
echo "2. Status do container:"
docker-compose ps backend

# Tamanho do banco (PostgreSQL)
echo "3. Tamanho do banco:"
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS banco;"

# Último backup
echo "4. Último backup:"
docker-compose exec backend ls -lt backups/ | head -2

# Logs de erro (últimas 24h)
echo "5. Erros nas últimas 24h:"
docker-compose logs --since 24h backend | grep -i error | wc -l

# Espaço em disco
echo "6. Espaço em disco:"
df -h | grep -E "(Filesystem|/var)"
```

### Verificação Semanal

```bash
#!/bin/bash
# health-check-weekly.sh

echo "=== Verificação Semanal BHUB ==="

# Integridade do banco (PostgreSQL)
echo "1. Integridade do banco:"
docker-compose exec db pg_isready -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}"
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT version_num FROM alembic_version;"

# Status do scheduler
echo "2. Status do scheduler:"
docker-compose exec backend python -c "
from app.jobs import get_scheduler_status
import json
print(json.dumps(get_scheduler_status(), indent=2))
"

# Estatísticas do banco (PostgreSQL)
echo "3. Estatísticas:"
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT (SELECT COUNT(*) FROM articles) AS articles, (SELECT COUNT(*) FROM users) AS users, (SELECT COUNT(*) FROM feeds) AS feeds;"

# Verificar backups
echo "4. Backups disponíveis:"
docker-compose exec backend ls -lh backups/ | wc -l
```

---

## 🔧 Manutenção

### Atualização de Código

```bash
# 1. Backup
docker-compose exec backend python -m scripts.backup_db

# 2. Parar aplicação
docker-compose down

# 3. Atualizar código
git pull origin main

# 4. Migrações
docker-compose run --rm backend alembic upgrade head

# 5. Rebuild
docker-compose up -d --build

# 6. Verificar
curl http://localhost:8000/health
```

### Banco que já existe e não tem `alembic_version`

Um banco cujo schema foi criado pelo próprio app (`Base.metadata.create_all`, via
`init_db()`) — o caminho que a produção percorreu até aqui — tem as tabelas mas **nenhuma**
linha em `alembic_version`. Nesse banco o passo 4 de
[Atualização de Código](#atualização-de-código) falha de duas formas diferentes, e as duas
levam à mesma crença:

- **rodado à mão**, o `alembic upgrade head` falha **ruidosamente**: rc≠0 e traceback de
  `DuplicateTableError`/`DuplicateColumnError`;
- **pelos scripts de deploy**, a falha é **engolida**: `scripts/vps/deploy.sh:129-133` e
  `scripts/vps/update.sh:76-80` convertem o rc≠0 do alembic em `warning` (o `update.sh`
  ainda manda o stderr para `/dev/null`) e o deploy segue.

Por isso este procedimento existe. E por isso ele mesmo tem de provar o alvo: um
`stamp head` no banco errado parece aplicado enquanto o banco de produção continua sem
`alembic_version` — ou pior, ganha uma linha de versão sem ter as tabelas.

**0. Fixe o alvo antes de rodar.** O caminho real de deploy é `bhub-backend-python/` na VPS
`/var/www/bhub/backend/` (é para lá que `upload-to-vps.sh:76` sobe a pasta) e o compose é o
**de dentro** desse diretório, `docker-compose.prod.yml` — o único com PostgreSQL. O
`docker-compose.prod.yml` da **raiz** do repositório fixa
`DATABASE_URL=sqlite+aiosqlite:///./bhub.db` (`:31`), então rodar o procedimento de lá
carimba um arquivo SQLite. Rode sempre de dentro de `bhub-backend-python/` (VPS:
`/var/www/bhub/backend/`) e com `-f docker-compose.prod.yml` explícito — o passo 4 daquela
seção depende do diretório atual.

A `DATABASE_URL` efetiva **não é determinável pelo repositório**: `alembic/env.py:40`
sobrescreve o `sqlalchemy.url` do `alembic.ini` com `settings.database_url`, que vem da
variável de ambiente `DATABASE_URL` do container; quem decide é o `.env` da VPS, que não é
versionado (`upload-to-vps.sh:67` o exclui do rsync). E todo `DATABASE_URL` que o
repositório escreve é SQLite (`config/env.production.template:29`,
`scripts/vps/deploy.sh:96`), enquanto o default do compose — quando a variável está ausente
— é o Postgres `postgresql+asyncpg://bhub:bhub@db:5432/bhub` (`docker-compose.prod.yml:32`).
Não presuma: **leia a URL que o container está usando** no passo 1a.

**O `alembic current` vazio não prova nada.** Medido em PostgreSQL 16: ele imprime o mesmo
(nada) num banco com as tabelas de `create_all`, num banco divergente e num banco **vazio**.
Num banco vazio o procedimento inteiro "passa" — `stamp head` rc=0, `current` respondendo
`009_feed_http_cache (head)`, `upgrade head` rc=0 — e o banco termina com **zero** tabelas
da aplicação (`alembic_version` é a única tabela que existe). É exatamente a crença que
esta seção existe para evitar, produzida com todos os sinais de sucesso que ela prescreve.

Procedimento medido contra PostgreSQL real (2026-09-17) — **uma vez**, antes do próximo
deploy:

```bash
# 0. Do diretório do backend, com o compose de produção explícito.
cd /var/www/bhub/backend        # no repositório: bhub-backend-python/
C="docker-compose -f docker-compose.prod.yml"

# 1a. PROVAR O ALVO: qual banco o container usa, e ele tem as tabelas da aplicação?
$C run --rm backend python -c "
import asyncio

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def main():
    url = settings.database_url
    print('DRIVER:', url.split('+')[0].split(':')[0], '| ALVO:', url.split('@')[-1])
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    await engine.dispose()
    app_tables = [n for n in names if n != 'alembic_version']
    print('TABELAS DA APLICACAO:', len(app_tables))
    for name in app_tables:
        print('  -', name)


asyncio.run(main())
"
# esperado: DRIVER: postgresql | ALVO: db:5432/bhub  e  TABELAS DA APLICACAO: 16
# 0 tabelas, DRIVER: sqlite, ou host/banco que não é o de produção => PARE AQUI,
# corrija o alvo (o .env e o -f do compose) e não carimbe nada.

# 1b. Só o 1a não basta: o schema existente corresponde ao head esperado?
$C run --rm backend alembic current    # esperado: vazio — mas isso só diz que falta a
                                       # tabela de versão, não valida o schema
```

As 16 tabelas da aplicação no head (medidas em PostgreSQL 16) — a mesma lista que o
`create_all` cria:

`analytics_events`, `analytics_metrics`, `analytics_sessions`, `article_authors`,
`article_categories`, `articles`, `authors`, `banners`, `categories`, `contact_messages`,
`feeds`, `pdf_metadata`, `refresh_tokens`, `scheduler_locks`, `translations_cache`, `users`.

O `current` vazio **não** é a verificação do schema. O schema de `create_all` carrega drift
**conhecido e medido** em relação à cadeia de migrações — em PostgreSQL 16 divergem **34
definições de coluna** e **6 objetos de índice** que existem em apenas um dos lados (mais 3
índices que existem nos dois com unicidade diferente), em 8 tabelas:

- `articles.is_open_access`, `article_categories.auto_created`, `article_categories.is_primary`
- `analytics_events`: `created_at`, `event_type`, `timestamp`, `updated_at`
- `analytics_metrics`: `article_downloads`, `article_views`, `created_at`, `searches`,
  `total_page_views`, `total_sessions`, `total_visitors`, `unique_visitors`, `updated_at`
- `analytics_sessions`: `created_at`, `events_count`, `last_activity`, `page_views`,
  `started_at`, `status`, `updated_at`
- `refresh_tokens`: `created_at`, `updated_at`
- `scheduler_locks`: `acquired_at`, `created_at`, `last_heartbeat`, `updated_at`
- `translations_cache`: `id`, `last_accessed_at`, `model`, `created_at`, `updated_at`
- índices só no head: `analytics_sessions_session_id_key`, `refresh_tokens_token_id_key`,
  `scheduler_locks_lock_name_key`, `translations_cache_content_hash_key`
- índices só no `create_all`: `ix_translations_cache_content_hash`,
  `ix_translations_cache_last_accessed_at`
- unicidade divergente nos dois lados: `ix_analytics_sessions_session_id`,
  `ix_refresh_tokens_token_id`, `ix_scheduler_locks_lock_name`

`stamp head` aceita tudo isso sem reclamar, então o passo 1b precisa ser fechado de uma das
duas formas — não há terceira:

- **verificação mínima executável:** num banco **descartável e vazio**, rode
  `alembic upgrade head` (`DATABASE_URL` apontando para ele) e compare o catálogo do banco
  descartável com o do banco existente — tabelas, colunas (`information_schema.columns`) e
  índices (`pg_indexes`). A diferença tem de ser exatamente a lista acima; qualquer item a
  mais é drift não inventariado, e aí o `stamp` ainda não é seguro;
- **ou aceite explícito, por escrito**, nomeando os itens acima (as 34 definições de coluna e
  os 6 índices) como aceitáveis no banco de produção.

Não use `alembic check` como aceite: medido, ele falha (rc=255, `New upgrade operations
detected`) mesmo num banco legitimamente no head.

```bash
# 2. Marcar o banco como já migrado até o head — só DEPOIS do 1a (16 tabelas) e do 1b
#    (drift verificado ou aceito por escrito).
$C run --rm backend alembic stamp head

# 3. Confirmar: o current responde o head e o upgrade vira no-op (rc=0).
$C run --rm backend alembic current
$C run --rm backend alembic upgrade head
# Isto confirma a VERSÃO, não o schema nem o alvo: as duas linhas também passam num banco
# vazio com uma linha em alembic_version (o passo 1a é a única prova do alvo).
```

`alembic stamp 000_baseline` **não** resolve, e é importante não confundir os dois:
esse banco já contém as tabelas de 001-009, então o `upgrade head` seguinte tenta
recriá-las e falha com `DuplicateTableError: relation "translations_cache" already
exists`, deixando `alembic_version` travado em `000_baseline`. A ordem de aplicação
importa: só marque `head` **depois** do passo 1a (o banco é o alvo certo e tem as tabelas) e
do passo 1b (o drift de `create_all` em relação à cadeia de migrações foi verificado ou
aceito por escrito, item por item).

### Limpeza de Dados

```bash
# Limpar logs antigos (manter últimos 30 dias)
docker-compose exec backend find logs/ -name "*.log" -mtime +30 -delete

# Limpar backups antigos (via script)
docker-compose exec backend python -m scripts.backup_db --retention-days 30

# Limpar cache de traduções antigas (se necessário)
docker-compose exec backend python -c "
from app.database import get_session_context
from app.models import TranslationCache
from sqlalchemy import delete
from datetime import datetime, timedelta
import asyncio
async def cleanup():
    async with get_session_context() as db:
        cutoff = datetime.utcnow() - timedelta(days=90)
        result = await db.execute(
            delete(TranslationCache).where(TranslationCache.created_at < cutoff)
        )
        await db.commit()
        print(f'Cache antigo removido: {result.rowcount}')
asyncio.run(cleanup())
"
```

---

## 🐛 Troubleshooting

### Logs Não Aparecem

```bash
# Verificar configuração de logging
docker-compose exec backend python -c "
from app.config import settings
print(f'Log level: {settings.log_level}')
print(f'Log dir: {settings.log_dir}')
"

# Verificar permissões
docker-compose exec backend ls -la logs/

# Verificar se logs estão sendo escritos
docker-compose exec backend tail -f logs/combined.log
```

### Performance Lenta

```bash
# Verificar uso de recursos
docker stats bhub-backend

# Verificar queries lentas (se habilitado)
docker-compose logs backend | grep -i "slow"

# Verificar tamanho do banco (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS banco;"

# Verificar índices (PostgreSQL)
docker-compose exec db psql -U "${POSTGRES_USER:-bhub}" -d "${POSTGRES_DB:-bhub}" \
  -c "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;"
```

### Erros de Conexão

```bash
# Verificar conectividade do banco
docker-compose exec backend python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        print('Conexão OK')
asyncio.run(test())
"

# Verificar variáveis de ambiente
docker-compose exec backend env | grep DATABASE_URL
```

---

## 📞 Escalação

Se os procedimentos acima não resolverem:

1. **Consultar logs detalhados**: `docker-compose logs --tail=500 backend`
2. **Verificar documentação**: `docs/deploy/`, `docs/seguranca/`
3. **Abrir issue**: Incluir logs, versão, ambiente
4. **Contato de emergência**: [definir contato]

---

**Última atualização**: Janeiro 2025
