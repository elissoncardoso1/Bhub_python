#!/bin/bash
# BHUB VPS Setup Script
# Configuração inicial da VPS para deploy do BHUB

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para log
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

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    error "Por favor, execute como root (use sudo)"
fi

log "Iniciando setup da VPS para BHUB..."

# 1. Atualizar sistema
log "Atualizando sistema..."
apt-get update
apt-get upgrade -y

# 2. Instalar dependências básicas
log "Instalando dependências básicas..."
apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop \
    nano \
    unzip

# 3. Instalar Node.js 18+
log "Instalando Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
    log "Node.js $(node --version) instalado"
else
    log "Node.js já instalado: $(node --version)"
fi

# 4. Instalar Python 3.12
log "Instalando Python 3.12..."
if ! command -v python3.12 &> /dev/null; then
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
    log "Python 3.12 instalado"
else
    log "Python 3.12 já instalado: $(python3.12 --version)"
fi

# 5. Instalar Docker
log "Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Adicionar usuário atual ao grupo docker (se não for root)
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
        log "Usuário $SUDO_USER adicionado ao grupo docker"
    fi
    
    # Instalar Docker Compose
    apt-get install -y docker-compose-plugin
    
    log "Docker instalado: $(docker --version)"
else
    log "Docker já instalado: $(docker --version)"
fi

# 6. Instalar Nginx
log "Instalando Nginx..."
if ! command -v nginx &> /dev/null; then
    apt-get install -y nginx
    systemctl enable nginx
    log "Nginx instalado"
else
    log "Nginx já instalado"
fi

# 7. Instalar Certbot
log "Instalando Certbot..."
if ! command -v certbot &> /dev/null; then
    apt-get install -y certbot python3-certbot-nginx
    log "Certbot instalado"
else
    log "Certbot já instalado"
fi

# 8. Instalar PM2 globalmente
log "Instalando PM2..."
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2
    pm2 install pm2-logrotate
    pm2 set pm2-logrotate:max_size 10M
    pm2 set pm2-logrotate:retain 7
    log "PM2 instalado"
else
    log "PM2 já instalado"
fi

# 9. Configurar Firewall
log "Configurando firewall UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
log "Firewall configurado"

# 10. Configurar Fail2ban
log "Configurando Fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban
log "Fail2ban configurado"

# 11. Criar estrutura de diretórios
log "Criando estrutura de diretórios..."
mkdir -p /var/www/bhub/{backend,frontend,backups,logs}
mkdir -p /var/backups/bhub
chown -R www-data:www-data /var/www/bhub
chown -R www-data:www-data /var/backups/bhub
log "Diretórios criados"

# 12. Configurar limites do sistema
log "Configurando limites do sistema..."
cat >> /etc/security/limits.conf << EOF

# BHUB limits
www-data soft nofile 65535
www-data hard nofile 65535
EOF

# 13. Otimizar sysctl para produção
log "Otimizando configurações do kernel..."
cat >> /etc/sysctl.conf << EOF

# BHUB optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_local_port_range = 10000 65535
vm.swappiness = 10
EOF
sysctl -p

log "Setup da VPS concluído com sucesso!"
log ""
log "Próximos passos:"
log "1. Configure o domínio apontando para este servidor"
log "2. Execute o script de deploy: ./scripts/vps/deploy.sh"
log "3. Configure SSL com: sudo certbot --nginx -d seu-dominio.com"

