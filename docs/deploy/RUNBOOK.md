# Runbook BHUB - Procedimentos Operacionais

**Versão**: 1.0.0  
**Data**: Janeiro 2025

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

### Backup Manual

```bash
# Dentro do container
docker-compose exec backend python -m scripts.backup_db

# Com opções
docker-compose exec backend python -m scripts.backup_db \
  --backup-dir /app/backups \
  --retention-days 30
```

### Restore

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

### Verificar Integridade

```bash
# Verificar banco atual
docker-compose exec backend python -c "
from scripts.backup_db import verify_database_integrity
from pathlib import Path
import asyncio
result = verify_database_integrity(Path('bhub.db'))
print('OK' if result else 'FALHOU')
"

# Verificar backup
docker-compose exec backend python -c "
from scripts.restore_db import verify_backup_integrity
from pathlib import Path
result = verify_backup_integrity(Path('backups/bhub_backup_20250115_020000.db'))
print('OK' if result else 'FALHOU')
"
```

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

**Sintomas**: Erros de SQLite, "database is locked", integridade falha

**Diagnóstico**:
```bash
# Verificar integridade
docker-compose exec backend python -m scripts.backup_db --no-verify

# Verificar locks
docker-compose exec backend sqlite3 bhub.db "PRAGMA integrity_check;"
```

**Solução**:
```bash
# 1. Parar aplicação
docker-compose down

# 2. Restaurar último backup
docker-compose run --rm backend python -m scripts.restore_db \
  backups/bhub_backup_YYYYMMDD_HHMMSS.db

# 3. Verificar integridade
docker-compose run --rm backend python -c "
from scripts.backup_db import verify_database_integrity
from pathlib import Path
result = verify_database_integrity(Path('bhub.db'))
print('OK' if result else 'FALHOU')
"

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

# Verificar tamanho do banco
docker-compose exec backend ls -lh bhub.db

# Verificar tamanho dos backups
docker-compose exec backend du -sh backups/

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

# Tamanho do banco
echo "3. Tamanho do banco:"
docker-compose exec backend ls -lh bhub.db

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

# Integridade do banco
echo "1. Integridade do banco:"
docker-compose exec backend python -c "
from scripts.backup_db import verify_database_integrity
from pathlib import Path
result = verify_database_integrity(Path('bhub.db'))
print('OK' if result else 'FALHOU')
"

# Status do scheduler
echo "2. Status do scheduler:"
docker-compose exec backend python -c "
from app.jobs import get_scheduler_status
import json
print(json.dumps(get_scheduler_status(), indent=2))
"

# Estatísticas do banco
echo "3. Estatísticas:"
docker-compose exec backend sqlite3 bhub.db "
SELECT 
    (SELECT COUNT(*) FROM articles) as articles,
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM feeds) as feeds;
"

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

# Verificar tamanho do banco
docker-compose exec backend ls -lh bhub.db

# Verificar índices
docker-compose exec backend sqlite3 bhub.db ".indices"
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
