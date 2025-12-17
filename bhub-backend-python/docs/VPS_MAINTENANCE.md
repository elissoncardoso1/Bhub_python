# Guia de Manutenção - BHUB VPS

Este guia contém comandos e procedimentos comuns para manutenção do BHUB em produção.

## Comandos Úteis

### Verificar Status dos Serviços

```bash
# Health check completo
bash scripts/vps/health-check.sh

# Status do Docker
docker-compose -f docker-compose.prod.yml ps

# Status do PM2
pm2 status
pm2 list

# Status do Nginx
sudo systemctl status nginx

# Status do sistema
htop
df -h
free -h
```

### Logs

```bash
# Backend (Docker)
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# Frontend (PM2)
pm2 logs bhub-frontend
pm2 logs bhub-frontend --lines 100

# Nginx
sudo tail -f /var/log/nginx/bhub-access.log
sudo tail -f /var/log/nginx/bhub-error.log

# Sistema
sudo journalctl -u docker -f
sudo journalctl -u nginx -f
```

### Reiniciar Serviços

```bash
# Backend
docker-compose -f docker-compose.prod.yml restart backend

# Frontend
pm2 restart bhub-frontend

# Nginx
sudo systemctl reload nginx
sudo systemctl restart nginx

# Todos os serviços
docker-compose -f docker-compose.prod.yml restart
pm2 restart all
```

## Backups

### Backup Manual

```bash
# Executar backup
bash scripts/vps/backup.sh

# Verificar backups
ls -lh /var/backups/bhub/
```

### Restaurar Backup

```bash
# Parar serviços
docker-compose -f docker-compose.prod.yml down
pm2 stop bhub-frontend

# Restaurar banco de dados
cd /var/www/bhub/backend/bhub-backend-python
cp /var/backups/bhub/bhub_YYYYMMDD_HHMMSS.db bhub.db

# Restaurar uploads
cd /var/www/bhub/backend/bhub-backend-python
tar -xzf /var/backups/bhub/uploads_YYYYMMDD_HHMMSS.tar.gz

# Reiniciar serviços
docker-compose -f docker-compose.prod.yml up -d
pm2 start bhub-frontend
```

### Configurar Backup Automático

Os backups já são configurados automaticamente. Para ajustar:

```bash
# Editar crontab
sudo crontab -e

# Adicionar linha (diário às 2h)
0 2 * * * /var/www/bhub/backend/bhub-backend-python/scripts/vps/backup.sh
```

## Atualizações

### Atualizar Código

```bash
# Usar script de atualização
cd /var/www/bhub/backend/bhub-backend-python
bash scripts/vps/update.sh main

# Ou manualmente:
cd /var/www/bhub/backend/bhub-backend-python
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
cd /var/www/bhub/frontend
git pull origin main
npm ci --production
npm run build
pm2 restart bhub-frontend
```

### Atualizar Dependências

```bash
# Backend
cd /var/www/bhub/backend/bhub-backend-python
docker-compose -f docker-compose.prod.yml build --no-cache

# Frontend
cd /var/www/bhub/frontend
npm update
npm run build
pm2 restart bhub-frontend
```

### Executar Migrações

```bash
cd /var/www/bhub/backend/bhub-backend-python
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Monitoramento

### Recursos do Sistema

```bash
# CPU e Memória
top
htop

# Disco
df -h
du -sh /var/www/bhub/*

# Rede
iftop
netstat -tulpn
```

### Performance da Aplicação

```bash
# Métricas do Docker
docker stats bhub-backend

# Métricas do PM2
pm2 monit

# Logs de performance
docker-compose -f docker-compose.prod.yml logs backend | grep -i "slow\|timeout\|error"
```

## Limpeza

### Limpar Logs Antigos

```bash
# Limpeza manual
sudo /usr/local/bin/bhub-clean-logs.sh

# Limpar logs do Docker
docker system prune -f

# Limpar logs do sistema
sudo journalctl --vacuum-time=30d
```

### Limpar Imagens Docker Não Utilizadas

```bash
docker system prune -a -f
docker volume prune -f
```

### Limpar Cache do NPM

```bash
cd /var/www/bhub/frontend
npm cache clean --force
```

## Troubleshooting Avançado

### Container não inicia

```bash
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs backend

# Verificar configuração
docker-compose -f docker-compose.prod.yml config

# Reconstruir do zero
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Problemas de Memória

```bash
# Ver uso de memória
free -h
docker stats

# Ajustar limites no docker-compose.prod.yml
# Editar seção deploy.resources.limits.memory
```

### Problemas de Disco

```bash
# Verificar espaço
df -h

# Encontrar arquivos grandes
du -h /var/www/bhub | sort -rh | head -20

# Limpar backups antigos
find /var/backups/bhub -mtime +30 -delete
```

### Problemas de Rede

```bash
# Testar conectividade
curl -I http://localhost:8000/health
curl -I http://localhost:3000

# Verificar portas
sudo netstat -tulpn | grep -E '8000|3000|80|443'

# Testar DNS
nslookup seudominio.com
```

## Manutenção Preventiva

### Tarefas Diárias

- Verificar logs de erro
- Verificar uso de recursos
- Verificar saúde dos serviços

### Tarefas Semanais

- Revisar backups
- Verificar espaço em disco
- Atualizar sistema (se necessário)

### Tarefas Mensais

- Revisar e limpar logs antigos
- Atualizar dependências (se necessário)
- Revisar configurações de segurança
- Testar procedimento de restore

## Segurança

### Atualizar Sistema

```bash
sudo apt update
sudo apt upgrade -y
```

### Verificar Certificado SSL

```bash
# Verificar expiração
sudo certbot certificates

# Renovar manualmente (se necessário)
sudo certbot renew --dry-run
```

### Revisar Firewall

```bash
# Ver regras ativas
sudo ufw status verbose

# Ver logs
sudo tail -f /var/log/ufw.log
```

### Verificar Acessos

```bash
# Últimos logins
last

# Tentativas de login falhadas
sudo grep "Failed password" /var/log/auth.log

# Acessos ao servidor
sudo tail -f /var/log/nginx/bhub-access.log | grep -v "health"
```

## Suporte

Em caso de problemas:

1. Verificar logs primeiro
2. Executar health-check.sh
3. Consultar este guia
4. Verificar documentação oficial dos componentes
5. Abrir issue no repositório (se aplicável)

