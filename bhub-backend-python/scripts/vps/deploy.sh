#!/bin/bash
# BHUB Deploy Script
# Script para fazer deploy completo da aplicação BHUB

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configurações
PROJECT_DIR="/var/www/bhub"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
REPO_URL="${REPO_URL:-}"  # Definir via variável de ambiente
DOMAIN="${DOMAIN:-}"      # Definir via variável de ambiente

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

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ] && [ ! -f "docker-compose.prod.yml" ]; then
    error "Execute este script a partir do diretório raiz do projeto"
fi

log "Iniciando deploy do BHUB..."

# 1. Verificar pré-requisitos
log "Verificando pré-requisitos..."
command -v docker >/dev/null 2>&1 || error "Docker não instalado"
command -v node >/dev/null 2>&1 || error "Node.js não instalado"
command -v pm2 >/dev/null 2>&1 || error "PM2 não instalado"
command -v nginx >/dev/null 2>&1 || error "Nginx não instalado"

# 2. Criar diretórios se não existirem
mkdir -p "$PROJECT_DIR"/{backend,frontend,backups,logs}
mkdir -p "$BACKEND_DIR"
mkdir -p "$FRONTEND_DIR"

# 3. Deploy do Backend
log "Fazendo deploy do backend..."

# Copiar arquivos do backend
if [ -d "bhub-backend-python" ]; then
    cp -r bhub-backend-python/* "$BACKEND_DIR/"
elif [ -f "Dockerfile" ] || [ -f "Dockerfile.prod" ]; then
    # Estamos no diretório do backend
    cp -r . "$BACKEND_DIR/"
else
    error "Diretório do backend não encontrado"
fi

cd "$BACKEND_DIR"

# Criar .env se não existir
if [ ! -f ".env" ]; then
    log "Criando arquivo .env..."
    if [ -f "config/.env.production.template" ]; then
        cp config/.env.production.template .env
        warning "Arquivo .env criado a partir do template. Configure as variáveis!"
    else
        # Criar .env básico
        cat > .env << EOF
# Database
DATABASE_URL=sqlite+aiosqlite:///./bhub.db

# Security - IMPORTANTE: Altere estes valores!
SECRET_KEY=$(openssl rand -hex 32)
CRON_SECRET=$(openssl rand -hex 16)

# App
DEBUG=false
ENVIRONMENT=production
ALLOWED_ORIGINS=https://${DOMAIN:-localhost},https://www.${DOMAIN:-localhost}

# AI Services (configure suas chaves)
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
HUGGINGFACE_API_KEY=

# Scheduler
ENABLE_SCHEDULER=true
EOF
        warning "Arquivo .env criado. Configure SECRET_KEY e outras variáveis!"
    fi
fi

# Validar SECRET_KEY
if grep -q "change-this-secret-key-in-production\|change-me-in-production" .env; then
    error "SECRET_KEY não foi alterado! Configure uma chave segura no .env"
fi

# Executar migrações
log "Executando migrações do banco de dados..."
if [ -f "alembic.ini" ]; then
    docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head || \
    docker-compose run --rm backend alembic upgrade head || \
    warning "Não foi possível executar migrações automaticamente"
fi

# Build e iniciar containers
log "Construindo e iniciando containers Docker..."
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml up -d --build
else
    docker-compose up -d --build
fi

# Aguardar backend ficar pronto
log "Aguardando backend ficar pronto..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log "Backend está respondendo!"
        break
    fi
    sleep 2
done

# 4. Deploy do Frontend
log "Fazendo deploy do frontend..."

# Localizar diretório do frontend
FRONTEND_SOURCE=""
if [ -d "../Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6" ]; then
    FRONTEND_SOURCE="../Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6"
elif [ -d "../../Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6" ]; then
    FRONTEND_SOURCE="../../Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6"
else
    error "Diretório do frontend não encontrado"
fi

# Copiar arquivos do frontend
cp -r "$FRONTEND_SOURCE"/* "$FRONTEND_DIR/"
cd "$FRONTEND_DIR"

# Instalar dependências
log "Instalando dependências do frontend..."
npm ci --production

# Criar .env.local
if [ ! -f ".env.local" ]; then
    log "Criando .env.local..."
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=https://${DOMAIN:-localhost}/api
NEXT_PUBLIC_ENABLE_ANALYTICS=true
EOF
fi

# Build do frontend
log "Fazendo build do frontend..."
npm run build

# Iniciar com PM2
log "Iniciando frontend com PM2..."
pm2 delete bhub-frontend 2>/dev/null || true
pm2 start npm --name "bhub-frontend" -- start
pm2 save

# 5. Configurar Nginx
log "Configurando Nginx..."
if [ -f "$BACKEND_DIR/config/nginx/bhub.conf" ]; then
    cp "$BACKEND_DIR/config/nginx/bhub.conf" /etc/nginx/sites-available/bhub
    
    # Substituir variáveis no arquivo
    sed -i "s/seudominio.com/${DOMAIN:-localhost}/g" /etc/nginx/sites-available/bhub
    
    # Ativar site
    ln -sf /etc/nginx/sites-available/bhub /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Testar configuração
    nginx -t || error "Configuração do Nginx inválida"
    
    # Recarregar Nginx
    systemctl reload nginx
    log "Nginx configurado"
else
    warning "Arquivo de configuração do Nginx não encontrado"
fi

# 6. Verificar saúde dos serviços
log "Verificando saúde dos serviços..."
sleep 5

# Backend
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    log "✓ Backend está funcionando"
else
    error "✗ Backend não está respondendo"
fi

# Frontend
if curl -f http://localhost:3000 >/dev/null 2>&1; then
    log "✓ Frontend está funcionando"
else
    warning "✗ Frontend pode não estar respondendo"
fi

# PM2
if pm2 list | grep -q "bhub-frontend.*online"; then
    log "✓ PM2 está gerenciando o frontend"
else
    warning "✗ PM2 pode não estar gerenciando o frontend corretamente"
fi

log ""
log "Deploy concluído com sucesso!"
log ""
log "Próximos passos:"
log "1. Configure SSL: sudo certbot --nginx -d ${DOMAIN:-seu-dominio.com}"
log "2. Verifique os logs: pm2 logs bhub-frontend"
log "3. Verifique o backend: docker-compose -f docker-compose.prod.yml logs -f"

