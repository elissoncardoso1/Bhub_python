#!/bin/bash
# Script de Upload para VPS - BHUB
# Facilita o upload do projeto para a VPS

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configurações (ajuste conforme necessário)
VPS_USER="${VPS_USER:-root}"
VPS_HOST="${VPS_HOST:-}"
VPS_PATH="/var/www/bhub"
SSH_PORT="${SSH_PORT:-22}"

# Verificar se host foi fornecido
if [ -z "$VPS_HOST" ]; then
    echo -e "${YELLOW}Configuração de Upload para VPS${NC}"
    echo ""
    read -p "IP ou hostname da VPS: " VPS_HOST
    read -p "Usuário SSH [$VPS_USER]: " input_user
    VPS_USER="${input_user:-$VPS_USER}"
    read -p "Porta SSH [$SSH_PORT]: " input_port
    SSH_PORT="${input_port:-$SSH_PORT}"
    echo ""
fi

echo -e "${GREEN}=== Upload BHUB para VPS ===${NC}"
echo "Host: $VPS_USER@$VPS_HOST:$SSH_PORT"
echo "Destino: $VPS_PATH"
echo ""

# Verificar se rsync está disponível
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}Erro: rsync não está instalado${NC}"
    echo "Instale com: brew install rsync (Mac) ou sudo apt install rsync (Linux)"
    exit 1
fi

# Verificar conexão
echo -e "${YELLOW}Verificando conexão com VPS...${NC}"
if ! ssh -p $SSH_PORT -o ConnectTimeout=5 $VPS_USER@$VPS_HOST "echo 'Conexão OK'" 2>/dev/null; then
    echo -e "${RED}Erro: Não foi possível conectar à VPS${NC}"
    echo "Verifique:"
    echo "  - IP/hostname correto"
    echo "  - SSH está rodando na VPS"
    echo "  - Firewall permite conexão SSH"
    echo "  - Chave SSH configurada (ou senha)"
    exit 1
fi

# Criar diretórios na VPS
echo -e "${YELLOW}Criando diretórios na VPS...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_HOST "sudo mkdir -p $VPS_PATH/{backend,frontend} && sudo chown -R \$USER:\$USER $VPS_PATH"

# Upload do Backend
echo ""
echo -e "${GREEN}Upload do Backend...${NC}"
rsync -avz --progress \
  -e "ssh -p $SSH_PORT" \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'bhub.db' \
  --exclude 'bhub.db-*' \
  --exclude 'app.db' \
  --exclude 'app.db-*' \
  --exclude 'uploads/' \
  --exclude 'logs/' \
  --exclude '.venv' \
  --exclude 'venv' \
  bhub-backend-python/ $VPS_USER@$VPS_HOST:$VPS_PATH/backend/

# Upload do Frontend
echo ""
echo -e "${GREEN}Upload do Frontend...${NC}"
if [ -d "Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6" ]; then
    rsync -avz --progress \
      -e "ssh -p $SSH_PORT" \
      --exclude '.git' \
      --exclude 'node_modules' \
      --exclude '.next' \
      --exclude '.env.local' \
      --exclude 'dev.log' \
      --exclude 'server.log' \
      Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6/ $VPS_USER@$VPS_HOST:$VPS_PATH/frontend/
else
    echo -e "${YELLOW}Diretório do frontend não encontrado. Pulando...${NC}"
fi

# Configurar permissões
echo ""
echo -e "${YELLOW}Configurando permissões...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
sudo chown -R www-data:www-data /var/www/bhub
sudo chmod -R 755 /var/www/bhub
sudo mkdir -p /var/www/bhub/backend/uploads /var/www/bhub/backend/logs
sudo chmod -R 775 /var/www/bhub/backend/uploads /var/www/bhub/backend/logs
ENDSSH

echo ""
echo -e "${GREEN}✓ Upload concluído com sucesso!${NC}"
echo ""
echo "Próximos passos na VPS:"
echo "  1. cd $VPS_PATH/backend"
echo "  2. cp config/env.production.template .env"
echo "  3. nano .env  # Configure as variáveis"
echo "  4. sudo bash scripts/vps/setup-vps.sh"
echo "  5. DOMAIN=seudominio.com bash scripts/vps/deploy.sh"
echo ""

