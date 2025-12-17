#!/bin/bash
# BHUB Health Check Script
# Verifica a saúde de todos os serviços

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXIT_CODE=0

check() {
    local name=$1
    local command=$2
    
    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name"
        EXIT_CODE=1
        return 1
    fi
}

echo "=== Verificação de Saúde do BHUB ==="
echo ""

# Backend
echo "Backend:"
check "  Backend respondendo (porta 8000)" "curl -f http://localhost:8000/health"
check "  Container Docker rodando" "docker ps | grep -q bhub-backend"

# Frontend
echo ""
echo "Frontend:"
check "  Frontend respondendo (porta 3000)" "curl -f http://localhost:3000"
check "  PM2 gerenciando frontend" "pm2 list | grep -q 'bhub-frontend.*online'"

# Nginx
echo ""
echo "Nginx:"
check "  Nginx rodando" "systemctl is-active --quiet nginx"
check "  Configuração válida" "nginx -t"

# Docker
echo ""
echo "Docker:"
check "  Docker rodando" "systemctl is-active --quiet docker"
check "  Docker Compose disponível" "docker compose version"

# Recursos do sistema
echo ""
echo "Recursos do Sistema:"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}✓${NC}   Espaço em disco: ${DISK_USAGE}% usado"
else
    echo -e "${RED}✗${NC}   Espaço em disco: ${DISK_USAGE}% usado (crítico!)"
    EXIT_CODE=1
fi

MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✓${NC}   Memória: ${MEM_USAGE}% usado"
else
    echo -e "${YELLOW}⚠${NC}   Memória: ${MEM_USAGE}% usado (alta)"
fi

# Logs recentes de erro
echo ""
echo "Logs (últimas 24h):"
ERROR_COUNT=$(journalctl -u docker --since "24 hours ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC}   Nenhum erro crítico nos logs do Docker"
else
    echo -e "${YELLOW}⚠${NC}   $ERROR_COUNT erros encontrados nos logs do Docker"
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Todos os serviços estão funcionando!${NC}"
else
    echo -e "${RED}✗ Alguns serviços apresentam problemas${NC}"
fi

exit $EXIT_CODE

