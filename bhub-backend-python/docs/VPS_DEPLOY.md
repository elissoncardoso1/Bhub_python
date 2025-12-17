# Guia de Deploy em VPS - BHUB

Este guia fornece instruções passo a passo para fazer deploy do BHUB em uma VPS da Hostinger (ou qualquer VPS Linux).

## Pré-requisitos

- VPS com Ubuntu 20.04+ ou Debian 11+
- Acesso root ou sudo
- Domínio configurado apontando para o IP da VPS
- Mínimo 2GB RAM, 2 vCPU, 20GB SSD (recomendado: 4GB RAM, 4 vCPU, 40GB SSD)

## Passo 1: Setup Inicial da VPS

Execute o script de setup que instala todas as dependências necessárias:

```bash
# Fazer upload do projeto para a VPS ou clonar do repositório
cd /var/www/bhub

# Executar script de setup (requer sudo)
sudo bash scripts/vps/setup-vps.sh
```

Este script irá:
- Atualizar o sistema
- Instalar Docker, Node.js, Nginx, Certbot, PM2
- Configurar firewall (UFW)
- Configurar Fail2ban
- Criar estrutura de diretórios
- Otimizar configurações do sistema

## Passo 2: Configurar Variáveis de Ambiente

Copie o template de variáveis de ambiente e configure:

```bash
cd /var/www/bhub/backend/bhub-backend-python
cp config/.env.production.template .env
nano .env
```

**IMPORTANTE**: Configure pelo menos:
- `SECRET_KEY`: Gere com `openssl rand -hex 32`
- `CRON_SECRET`: Gere com `openssl rand -hex 16`
- `ALLOWED_ORIGINS`: Seu domínio (ex: `https://seudominio.com,https://www.seudominio.com`)
- `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`: Suas chaves de API

## Passo 3: Deploy da Aplicação

Execute o script de deploy:

```bash
cd /var/www/bhub/backend/bhub-backend-python
DOMAIN=seudominio.com bash scripts/vps/deploy.sh
```

Este script irá:
- Fazer build do backend (Docker)
- Executar migrações do banco de dados
- Fazer build do frontend
- Iniciar serviços com PM2
- Configurar Nginx

## Passo 4: Configurar SSL/HTTPS

Após o deploy, configure o certificado SSL:

```bash
sudo certbot --nginx -d seudominio.com -d www.seudominio.com
```

O Certbot irá:
- Obter certificado Let's Encrypt
- Configurar renovação automática
- Atualizar configuração do Nginx

## Passo 5: Verificar Deploy

Verifique se tudo está funcionando:

```bash
# Health check
bash scripts/vps/health-check.sh

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
pm2 logs bhub-frontend

# Testar endpoints
curl https://seudominio.com/health
curl https://seudominio.com/api/v1/articles
```

## Configuração do Nginx

O arquivo de configuração está em `config/nginx/bhub.conf`. Para aplicá-lo:

```bash
# Copiar configuração
sudo cp config/nginx/bhub.conf /etc/nginx/sites-available/bhub

# Substituir domínio
sudo sed -i 's/seudominio.com/SEU-DOMINIO.com/g' /etc/nginx/sites-available/bhub

# Ativar site
sudo ln -sf /etc/nginx/sites-available/bhub /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar e recarregar
sudo nginx -t
sudo systemctl reload nginx
```

## Estrutura de Diretórios

Após o deploy, a estrutura será:

```
/var/www/bhub/
├── backend/
│   └── bhub-backend-python/
│       ├── .env
│       ├── bhub.db
│       ├── uploads/
│       └── logs/
├── frontend/
│   ├── .next/
│   └── .env.local
├── backups/
└── logs/
```

## Checklist de Segurança

Antes de colocar em produção, verifique:

- [ ] `SECRET_KEY` foi alterado e tem pelo menos 32 caracteres
- [ ] `CRON_SECRET` está configurado
- [ ] `ALLOWED_ORIGINS` não contém wildcards (*)
- [ ] `DEBUG=false` em produção
- [ ] `ENVIRONMENT=production`
- [ ] SSL/HTTPS configurado e funcionando
- [ ] Firewall (UFW) bloqueando portas desnecessárias
- [ ] Backups automáticos configurados
- [ ] Logs sendo rotacionados
- [ ] Health checks funcionando

## Troubleshooting

### Backend não inicia

```bash
# Ver logs do Docker
docker-compose -f docker-compose.prod.yml logs -f backend

# Verificar se porta está livre
sudo netstat -tulpn | grep 8000

# Reiniciar container
docker-compose -f docker-compose.prod.yml restart backend
```

### Frontend não inicia

```bash
# Ver logs do PM2
pm2 logs bhub-frontend

# Verificar status
pm2 status

# Reiniciar
pm2 restart bhub-frontend
```

### Nginx retorna 502

```bash
# Verificar se backend está rodando
curl http://localhost:8000/health

# Verificar logs do Nginx
sudo tail -f /var/log/nginx/bhub-error.log

# Verificar configuração
sudo nginx -t
```

### Erro de permissões

```bash
# Corrigir permissões
sudo chown -R www-data:www-data /var/www/bhub
sudo chmod -R 755 /var/www/bhub
```

### Banco de dados bloqueado

```bash
# Se SQLite estiver bloqueado
cd /var/www/bhub/backend/bhub-backend-python
docker-compose -f docker-compose.prod.yml down
rm -f bhub.db-shm bhub.db-wal
docker-compose -f docker-compose.prod.yml up -d
```

## Próximos Passos

Após o deploy bem-sucedido:

1. Configure backups automáticos (já configurado via cron)
2. Configure monitoramento (opcional: Sentry, Datadog, etc.)
3. Configure CDN para assets estáticos (opcional: Cloudflare)
4. Configure alertas de saúde (opcional)

## Referências

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

