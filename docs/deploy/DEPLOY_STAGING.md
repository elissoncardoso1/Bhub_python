# Deploy BHUB - Staging/Beta

**Versão**: 1.0.0  
**Data**: Janeiro 2025  
**Status**: ✅ Pronto para deploy controlado

---

## 📋 Visão Geral

Este documento descreve o processo de deploy do BHUB em ambiente de **staging/beta**. Este ambiente é adequado para:
- Testes controlados com usuários limitados
- Validação de funcionalidades antes de produção
- Desenvolvimento e testes de integração

**⚠️ IMPORTANTE**: Este ambiente NÃO é adequado para tráfego público ou produção.

---

## 🎯 Pré-requisitos

### Infraestrutura
- VPS ou servidor com Docker e Docker Compose instalados
- Mínimo 2GB RAM, 2 CPUs, 20GB disco
- Acesso SSH ao servidor
- Domínio configurado (opcional, pode usar IP)

### Software
- Docker 20.10+
- Docker Compose 2.0+
- Git

---

## 🚀 Passo a Passo de Deploy

### 1. Preparar Ambiente

```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Criar diretório do projeto
mkdir -p /var/www/bhub
cd /var/www/bhub

# Clonar repositório (ou fazer upload)
git clone https://github.com/seu-usuario/bhub-backend-python.git
cd bhub-backend-python
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar template de ambiente
cp config/env.production.template .env

# Editar .env com suas configurações
nano .env
```

**Variáveis obrigatórias**:

```env
# App
APP_NAME=BHUB
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=staging

# Database
DATABASE_URL=sqlite+aiosqlite:///./bhub.db

# Security (GERAR NOVA CHAVE!)
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
ALLOWED_ORIGINS=https://staging.seu-dominio.com,http://localhost:8000

# AI Services
DEEPSEEK_API_KEY=<sua-chave>
OPENROUTER_API_KEY=<sua-chave>

# Scheduler
ENABLE_SCHEDULER=true
SCHEDULER_MODE=app
SYNC_INTERVAL_HOURS=1
CRON_SECRET=<gerar-secret-aleatorio>

# Backup
BACKUP_RETENTION_DAYS=30
```

**Gerar SECRET_KEY**:
```bash
openssl rand -hex 32
```

### 3. Executar Migrações

```bash
# Dentro do container ou localmente
docker-compose run --rm backend alembic upgrade head
```

### 4. Criar Usuário Admin

```bash
docker-compose run --rm backend python -m scripts.create_superuser
```

### 5. Iniciar Aplicação

```bash
# Build e iniciar
docker-compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 6. Verificar Saúde

```bash
# Health check
curl http://localhost:8000/health

# Deve retornar:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "database": "connected",
#   "ml_model": "loaded",
#   "timestamp": "..."
# }
```

**⚠️ IMPORTANTE**: Os testes automatizados (`pytest`) devem ser executados **ANTES** do deploy, em ambiente local ou CI/CD. No VPS, apenas validações básicas (health check) são necessárias.

---

## 🔧 Configuração de Backup Automático

### Opção 1: Cron Job

```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 2h da manhã)
0 2 * * * cd /var/www/bhub/bhub-backend-python && docker-compose exec -T backend python -m scripts.backup_db >> /var/log/bhub-backup.log 2>&1
```

### Opção 2: Script Systemd Timer

Criar `/etc/systemd/system/bhub-backup.service`:
```ini
[Unit]
Description=BHUB Database Backup
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker-compose -f /var/www/bhub/bhub-backend-python/docker-compose.prod.yml exec -T backend python -m scripts.backup_db
WorkingDirectory=/var/www/bhub/bhub-backend-python
```

Criar `/etc/systemd/system/bhub-backup.timer`:
```ini
[Unit]
Description=BHUB Database Backup Timer
Requires=bhub-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Ativar:
```bash
sudo systemctl enable bhub-backup.timer
sudo systemctl start bhub-backup.timer
```

---

## ✅ Validação Pós-Deploy

### Checklist

- [ ] **Testes executados ANTES do deploy** (localmente ou CI/CD)
  - [ ] Testes smoke: `pytest tests/test_smoke.py -v`
  - [ ] Testes básicos: `pytest tests/test_articles.py -v`
- [ ] Health check responde corretamente (`/health`)
- [ ] Login funciona (`/api/v1/auth/login`)
- [ ] Admin acessível (`/admin`)
- [ ] Scheduler está rodando (verificar logs)
- [ ] Backup automático configurado e testado
- [ ] Logs sendo gerados (`logs/`)

### Comandos de Validação

**No VPS (após deploy)**:
```bash
# Health check
curl http://localhost:8000/health

# Verificar scheduler
docker-compose exec backend python -c "from app.jobs import get_scheduler_status; import asyncio; print(asyncio.run(get_scheduler_status()))"

# Verificar logs
docker-compose logs --tail=100 backend

# Testar backup
docker-compose exec backend python -m scripts.backup_db

# Listar backups
docker-compose exec backend python -m scripts.restore_db --list
```

**Antes do deploy (localmente)**:
```bash
# Executar testes completos
cd bhub-backend-python
pytest tests/ -v

# Testes específicos
pytest tests/test_smoke.py -v
pytest tests/test_articles.py -v
```

---

## 🔄 Atualização

```bash
# 1. Fazer backup antes de atualizar
docker-compose exec backend python -m scripts.backup_db

# 2. Parar aplicação
docker-compose -f docker-compose.prod.yml down

# 3. Atualizar código
git pull origin main

# 4. Executar migrações (se houver)
docker-compose run --rm backend alembic upgrade head

# 5. Rebuild e reiniciar
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 🐛 Troubleshooting

### Aplicação não inicia

```bash
# Verificar logs
docker-compose logs backend

# Verificar variáveis de ambiente
docker-compose exec backend env | grep -E "(SECRET_KEY|DATABASE_URL)"

# Verificar banco de dados
docker-compose exec backend python -c "from app.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Scheduler não executa

```bash
# Verificar se está habilitado
docker-compose exec backend python -c "from app.config import settings; print(f'Scheduler: {settings.enable_scheduler}, Mode: {settings.scheduler_mode}')"

# Verificar locks
docker-compose exec backend python -c "from app.database import get_session_context; from app.models import SchedulerLock; from sqlalchemy import select; import asyncio; async def check(): async with get_session_context() as db: result = await db.execute(select(SchedulerLock)); print([l.lock_name for l in result.scalars()]); asyncio.run(check())"
```

### Backup falha

```bash
# Verificar permissões
ls -la backups/

# Verificar espaço em disco
df -h

# Testar backup manualmente
docker-compose exec backend python -m scripts.backup_db --no-verify
```

---

## 📊 Monitoramento Básico

### Logs

```bash
# Ver logs em tempo real
docker-compose logs -f backend

# Ver logs de erro
docker-compose logs backend | grep ERROR

# Ver logs do scheduler
docker-compose logs backend | grep scheduler
```

### Métricas

```bash
# Uso de recursos
docker stats bhub-backend

# Tamanho do banco
docker-compose exec backend ls -lh bhub.db

# Espaço em disco
df -h
```

---

## 🔐 Segurança

### Checklist de Segurança Staging

- [x] SECRET_KEY gerado e configurado
- [x] DEBUG=false
- [x] ALLOWED_ORIGINS configurado
- [x] Acesso restrito (firewall/IP whitelist)
- [x] Backup automático configurado
- [x] Logs sendo monitorados

---

## 📝 Notas

- **Volume estimado**: Baixo (staging/beta)
- **Usuários**: Limitados (acesso controlado)
- **Tráfego**: Controlado
- **Disponibilidade**: Não crítica (pode ter downtime)

---

## 🚨 Próximos Passos

Após validar staging, seguir para:
1. Revisar `DEPLOY_PROD.md` para requisitos de produção
2. Resolver todos os bloqueadores listados em `MAPA_EXECUCAO_DEPLOY.md`
3. Executar testes completos
4. Revisar `SECURITY_DECISIONS.md`

---

**Última atualização**: Janeiro 2025
