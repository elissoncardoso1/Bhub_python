#!/bin/bash
# BHUB Backup Script
# Script para fazer backup do banco de dados e uploads

set -e

# Configurações
BACKUP_DIR="/var/backups/bhub"
PROJECT_DIR="/var/www/bhub"
BACKEND_DIR="$PROJECT_DIR/backend"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)

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

# Criar diretório de backup
mkdir -p "$BACKUP_DIR"

log "Iniciando backup do BHUB..."

# 1. Backup do banco de dados
log "Fazendo backup do banco de dados..."
DB_FILE="$BACKEND_DIR/bhub-backend-python/bhub.db"
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_DIR/bhub_${DATE}.db"
    log "✓ Banco de dados copiado"
elif [ -f "$BACKEND_DIR/bhub.db" ]; then
    cp "$BACKEND_DIR/bhub.db" "$BACKUP_DIR/bhub_${DATE}.db"
    log "✓ Banco de dados copiado"
else
    warning "Arquivo do banco de dados não encontrado"
fi

# 2. Backup dos uploads
log "Fazendo backup dos uploads..."
UPLOADS_DIR="$BACKEND_DIR/bhub-backend-python/uploads"
if [ -d "$UPLOADS_DIR" ]; then
    tar -czf "$BACKUP_DIR/uploads_${DATE}.tar.gz" -C "$BACKEND_DIR/bhub-backend-python" uploads/
    log "✓ Uploads comprimidos"
elif [ -d "$BACKEND_DIR/uploads" ]; then
    tar -czf "$BACKUP_DIR/uploads_${DATE}.tar.gz" -C "$BACKEND_DIR" uploads/
    log "✓ Uploads comprimidos"
else
    warning "Diretório de uploads não encontrado"
fi

# 3. Backup do arquivo .env (sem expor secrets em logs)
log "Fazendo backup do .env..."
ENV_FILE="$BACKEND_DIR/bhub-backend-python/.env"
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$BACKUP_DIR/env_${DATE}.env"
    chmod 600 "$BACKUP_DIR/env_${DATE}.env"
    log "✓ Arquivo .env copiado"
elif [ -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env" "$BACKUP_DIR/env_${DATE}.env"
    chmod 600 "$BACKUP_DIR/env_${DATE}.env"
    log "✓ Arquivo .env copiado"
fi

# 4. Criar arquivo de índice
log "Criando índice de backups..."
cat > "$BACKUP_DIR/index.txt" << EOF
# BHUB Backup Index
# Gerado em: $(date)

Backups disponíveis:
$(ls -lh "$BACKUP_DIR"/*.db "$BACKUP_DIR"/*.tar.gz "$BACKUP_DIR"/*.env 2>/dev/null | awk '{print $9, $5, $6, $7, $8}')

Total de backups: $(ls -1 "$BACKUP_DIR"/*.db 2>/dev/null | wc -l)
EOF

# 5. Limpar backups antigos
log "Limpando backups antigos (mantendo últimos $RETENTION_DAYS dias)..."
find "$BACKUP_DIR" -name "*.db" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.env" -mtime +$RETENTION_DAYS -delete
log "✓ Backups antigos removidos"

# 6. Calcular tamanho total
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Tamanho total dos backups: $TOTAL_SIZE"

log ""
log "Backup concluído com sucesso!"
log "Localização: $BACKUP_DIR"
log "Backups mantidos: últimos $RETENTION_DAYS dias"

