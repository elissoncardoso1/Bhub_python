#!/bin/bash
# Script de Deploy Docker para BHUB
# Uso: ./deploy-docker.sh [--build] [--restart]

set -e

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funções
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
if [ ! -f "docker-compose.prod.yml" ]; then
    error "Execute este script a partir do diretório raiz do projeto"
fi

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    error "Docker não está instalado. Instale Docker primeiro."
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose não está instalado. Instale Docker Compose primeiro."
fi

# Verificar se .env existe
if [ ! -f ".env" ]; then
    warning "Arquivo .env não encontrado. Criando a partir do template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warning "Configure as variáveis no arquivo .env antes de continuar!"
        exit 1
    elif [ -f "env.example" ]; then
        cp env.example .env
        warning "Configure as variáveis no arquivo .env antes de continuar!"
        exit 1
    else
        error "Arquivo .env não encontrado e template não existe. Crie o arquivo .env manualmente."
    fi
fi

# Parse argumentos
BUILD=false
RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        *)
            error "Argumento desconhecido: $1"
            ;;
    esac
done

log "Iniciando deploy do BHUB..."

# Parar containers se --restart
if [ "$RESTART" = true ]; then
    log "Parando containers existentes..."
    docker-compose -f docker-compose.prod.yml down
fi

# Construir imagens se --build ou primeira vez
if [ "$BUILD" = true ] || [ -z "$(docker images -q bhub-backend 2>/dev/null)" ]; then
    log "Construindo imagens Docker..."
    docker-compose -f docker-compose.prod.yml build --no-cache
else
    log "Pulando build (use --build para forçar reconstrução)"
fi

# Iniciar containers
log "Iniciando containers..."
docker-compose -f docker-compose.prod.yml up -d

# Aguardar serviços ficarem prontos
log "Aguardando serviços ficarem prontos..."
sleep 10

# Verificar saúde dos serviços
log "Verificando saúde dos serviços..."

BACKEND_OK=false
FRONTEND_OK=false

for i in {1..30}; do
    if docker exec bhub-backend curl -f http://localhost:8000/health >/dev/null 2>&1; then
        BACKEND_OK=true
        break
    fi
    sleep 2
done

for i in {1..30}; do
    if docker exec bhub-frontend node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" >/dev/null 2>&1; then
        FRONTEND_OK=true
        break
    fi
    sleep 2
done

# Resultado
echo ""
if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ]; then
    log "✓ Deploy concluído com sucesso!"
    log "✓ Backend está funcionando"
    log "✓ Frontend está funcionando"
    echo ""
    log "Status dos containers:"
    docker-compose -f docker-compose.prod.yml ps
    echo ""
    log "Para ver os logs:"
    log "  docker-compose -f docker-compose.prod.yml logs -f"
else
    error "Deploy pode ter falhado. Verifique os logs: docker-compose -f docker-compose.prod.yml logs"
fi

