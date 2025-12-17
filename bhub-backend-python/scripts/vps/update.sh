#!/bin/bash
# BHUB Update Script
# Script para atualizar a aplicação de forma segura

set -e

# Configurações
PROJECT_DIR="/var/www/bhub"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKUP_DIR="/var/backups/bhub"

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar argumentos
if [ -z "$1" ]; then
    error "Uso: $0 <branch|tag|commit> [--skip-backup]"
fi

UPDATE_TARGET="$1"
SKIP_BACKUP="${2:-}"

log "Iniciando atualização do BHUB para: $UPDATE_TARGET"

# 1. Fazer backup antes de atualizar
if [ "$SKIP_BACKUP" != "--skip-backup" ]; then
    log "Fazendo backup antes da atualização..."
    "$(dirname "$0")/backup.sh" || warning "Backup falhou, mas continuando..."
else
    warning "Backup pulado (--skip-backup)"
fi

# 2. Atualizar Backend
log "Atualizando backend..."
cd "$BACKEND_DIR"

# Se for um repositório git
if [ -d ".git" ]; then
    git fetch origin
    git checkout "$UPDATE_TARGET" || error "Não foi possível fazer checkout de $UPDATE_TARGET"
    git pull origin "$UPDATE_TARGET" 2>/dev/null || true
else
    warning "Diretório não é um repositório git. Atualização manual necessária."
fi

# Reconstruir e reiniciar containers
log "Reconstruindo containers Docker..."
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d --build
else
    docker-compose down
    docker-compose up -d --build
fi

# Executar migrações
log "Executando migrações..."
sleep 5  # Aguardar container iniciar
if [ -f "alembic.ini" ]; then
    docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head 2>/dev/null || \
    docker-compose exec -T backend alembic upgrade head 2>/dev/null || \
    warning "Não foi possível executar migrações automaticamente"
fi

# 3. Atualizar Frontend
log "Atualizando frontend..."
cd "$FRONTEND_DIR"

# Se for um repositório git
if [ -d ".git" ]; then
    git fetch origin
    git checkout "$UPDATE_TARGET" || error "Não foi possível fazer checkout de $UPDATE_TARGET"
    git pull origin "$UPDATE_TARGET" 2>/dev/null || true
else
    warning "Diretório não é um repositório git. Atualização manual necessária."
fi

# Instalar dependências e rebuild
log "Instalando dependências do frontend..."
npm ci --production

log "Fazendo build do frontend..."
npm run build

# Reiniciar PM2
log "Reiniciando frontend..."
pm2 restart bhub-frontend

# 4. Verificar saúde dos serviços
log "Verificando saúde dos serviços..."
sleep 10

BACKEND_OK=false
FRONTEND_OK=false

for i in {1..10}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        BACKEND_OK=true
        break
    fi
    sleep 2
done

for i in {1..10}; do
    if curl -f http://localhost:3000 >/dev/null 2>&1; then
        FRONTEND_OK=true
        break
    fi
    sleep 2
done

# 5. Resultado
echo ""
if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ]; then
    log "✓ Atualização concluída com sucesso!"
    log "✓ Backend está funcionando"
    log "✓ Frontend está funcionando"
else
    error "✗ Atualização pode ter falhado. Verifique os logs."
fi

log ""
log "Para verificar logs:"
log "  Backend: docker-compose -f docker-compose.prod.yml logs -f"
log "  Frontend: pm2 logs bhub-frontend"

