#!/bin/bash
# BHUB Log Rotation Setup
# Configura rotação de logs para a aplicação

set -e

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    error "Por favor, execute como root (use sudo)"
fi

log "Configurando rotação de logs..."

# 1. Configurar logrotate para logs do backend
log "Configurando logrotate para backend..."
cat > /etc/logrotate.d/bhub-backend << 'EOF'
/var/www/bhub/backend/bhub-backend-python/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        docker restart bhub-backend 2>/dev/null || true
    endscript
}
EOF

# 2. Configurar logrotate para logs do Nginx
log "Configurando logrotate para Nginx (já deve existir, mas verificando)..."
if [ ! -f "/etc/logrotate.d/nginx" ]; then
    cat > /etc/logrotate.d/nginx << 'EOF'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
EOF
fi

# 3. Configurar PM2 log rotation (já configurado no setup, mas verificando)
log "Verificando configuração do PM2..."
if command -v pm2 &> /dev/null; then
    pm2 install pm2-logrotate 2>/dev/null || true
    pm2 set pm2-logrotate:max_size 10M
    pm2 set pm2-logrotate:retain 7
    pm2 set pm2-logrotate:compress true
    log "✓ PM2 log rotation configurado"
fi

# 4. Configurar rotação de logs do Docker
log "Configurando rotação de logs do Docker..."
if [ -f "/etc/docker/daemon.json" ]; then
    # Backup do arquivo existente
    cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
fi

# Adicionar configuração de logs do Docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# Reiniciar Docker se necessário
if systemctl is-active --quiet docker; then
    log "Reiniciando Docker para aplicar configurações de log..."
    systemctl restart docker
fi

# 5. Criar script de limpeza manual
log "Criando script de limpeza de logs..."
cat > /usr/local/bin/bhub-clean-logs.sh << 'EOF'
#!/bin/bash
# Limpeza manual de logs antigos

echo "Limpando logs antigos..."

# Logs do backend
find /var/www/bhub/backend/bhub-backend-python/logs -name "*.log.*" -mtime +30 -delete

# Logs do Docker
docker system prune -f --volumes

# Logs do sistema
journalctl --vacuum-time=30d

echo "Limpeza concluída!"
EOF

chmod +x /usr/local/bin/bhub-clean-logs.sh

log ""
log "Configuração de rotação de logs concluída!"
log ""
log "Configurações aplicadas:"
log "  - Backend: rotação diária, 30 dias de retenção"
log "  - Nginx: rotação diária, 52 dias de retenção"
log "  - PM2: máximo 10MB por arquivo, 7 arquivos"
log "  - Docker: máximo 10MB por arquivo, 3 arquivos"
log ""
log "Para limpeza manual: sudo /usr/local/bin/bhub-clean-logs.sh"

