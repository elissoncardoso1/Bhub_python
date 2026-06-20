# 🐳 Guia de Deploy Docker - BHUB

Este guia explica como fazer o deploy completo do BHUB usando Docker em produção.

## 📋 Pré-requisitos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Acesso SSH ao servidor VPS
- Domínio configurado (opcional, mas recomendado)

## 🚀 Deploy Completo

### 1. Preparar o Servidor

```bash
# Conectar ao VPS
ssh usuario@seu-vps

# Instalar Docker (se não estiver instalado)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalação
docker --version
docker-compose --version
```

### 2. Preparar o Projeto no Servidor

```bash
# Criar diretório do projeto
sudo mkdir -p /var/www/bhub
sudo chown $USER:$USER /var/www/bhub
cd /var/www/bhub

# Clonar o repositório ou fazer upload dos arquivos
# Se usar Git:
git clone seu-repositorio.git .

# Ou fazer upload via SCP:
# scp -r /caminho/local/bhub/* usuario@vps:/var/www/bhub/
```

### 3. Configurar Variáveis de Ambiente

```bash
cd /var/www/bhub

# Criar arquivo .env na raiz
cat > .env << EOF
# Backend
SECRET_KEY=$(openssl rand -hex 32)
CRON_SECRET=$(openssl rand -hex 16)
DEBUG=false
ENVIRONMENT=production
ALLOWED_ORIGINS=https://seudominio.com,https://www.seudominio.com

# AI Services
DEEPSEEK_API_KEY=sua-chave-aqui
OPENROUTER_API_KEY=sua-chave-aqui
HUGGINGFACE_API_KEY=sua-chave-aqui

# Scheduler
ENABLE_SCHEDULER=true
SYNC_INTERVAL_HOURS=1

# Frontend
NEXT_PUBLIC_API_URL=https://seudominio.com/api/v1
NEXT_PUBLIC_ENABLE_ANALYTICS=true
EOF

# Configurar permissões
chmod 600 .env
```

### 4. Construir e Iniciar os Containers

```bash
cd /var/www/bhub

# Construir as imagens
docker-compose -f docker-compose.prod.yml build

# Iniciar os serviços
docker-compose -f docker-compose.prod.yml up -d

# Verificar status
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Configurar Nginx (Reverso Proxy)

```bash
# Instalar Nginx
sudo apt update
sudo apt install -y nginx

# Criar configuração do Nginx
sudo nano /etc/nginx/sites-available/bhub
```

Conteúdo do arquivo `/etc/nginx/sites-available/bhub`:

```nginx
# Upstream para backend
upstream backend {
    server localhost:8000;
}

# Upstream para frontend
upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name seudominio.com www.seudominio.com;

    # Redirecionar para HTTPS (após configurar SSL)
    # return 301 https://$server_name$request_uri;

    # Ou servir HTTP temporariamente
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API routes para backend
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/bhub /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

### 6. Configurar SSL com Certbot (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obter certificado SSL
sudo certbot --nginx -d seudominio.com -d www.seudominio.com

# Renovar automaticamente (já configurado por padrão)
sudo certbot renew --dry-run
```

### 7. Verificar Funcionamento

```bash
# Verificar containers
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend

# Testar endpoints
curl http://localhost:8000/health  # Backend
curl http://localhost:3000          # Frontend
curl https://seudominio.com         # Site público
```

## 🔄 Comandos Úteis

### Gerenciamento de Containers

```bash
# Iniciar serviços
docker-compose -f docker-compose.prod.yml up -d

# Parar serviços
docker-compose -f docker-compose.prod.yml down

# Reiniciar serviços
docker-compose -f docker-compose.prod.yml restart

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f [servico]

# Reconstruir após mudanças
docker-compose -f docker-compose.prod.yml up -d --build

# Ver uso de recursos
docker stats
```

### Backup

```bash
# Backup do banco de dados
docker cp bhub-backend:/app/bhub.db ./backup-$(date +%Y%m%d).db

# Backup dos uploads
tar -czf uploads-backup-$(date +%Y%m%d).tar.gz ./bhub-backend-python/uploads/

# Backup completo
tar -czf bhub-backup-$(date +%Y%m%d).tar.gz \
  ./bhub-backend-python/bhub.db \
  ./bhub-backend-python/uploads/ \
  ./bhub-backend-python/logs/
```

### Atualização

```bash
# 1. Fazer backup
# (usar comandos acima)

# 2. Atualizar código
git pull origin main
# ou fazer upload dos arquivos atualizados

# 3. Reconstruir e reiniciar
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Verificar logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔍 Troubleshooting

### Containers não iniciam

```bash
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs

# Verificar recursos do sistema
docker stats

# Verificar espaço em disco
df -h
```

### Backend não responde

```bash
# Verificar se o container está rodando
docker ps | grep bhub-backend

# Ver logs do backend
docker-compose -f docker-compose.prod.yml logs backend

# Testar health check
docker exec bhub-backend curl http://localhost:8000/health
```

### Frontend não responde

```bash
# Verificar se o container está rodando
docker ps | grep bhub-frontend

# Ver logs do frontend
docker-compose -f docker-compose.prod.yml logs frontend

# Verificar build
docker-compose -f docker-compose.prod.yml build frontend --no-cache
```

### Problemas de rede

```bash
# Verificar rede Docker
docker network ls
docker network inspect bhub_bhub-network

# Verificar conectividade entre containers
docker exec bhub-frontend ping -c 3 backend
```

### Limpar e recomeçar

```bash
# Parar e remover containers
docker-compose -f docker-compose.prod.yml down

# Remover imagens
docker-compose -f docker-compose.prod.yml down --rmi all

# Limpar volumes (CUIDADO: remove dados!)
docker-compose -f docker-compose.prod.yml down -v

# Reconstruir do zero
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoramento

### Ver uso de recursos

```bash
# Uso em tempo real
docker stats

# Uso de disco
docker system df
```

### Logs centralizados

```bash
# Ver todos os logs
docker-compose -f docker-compose.prod.yml logs -f

# Logs de um serviço específico
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# Últimas 100 linhas
docker-compose -f docker-compose.prod.yml logs --tail=100
```

## 🔒 Segurança

### Boas Práticas

1. **Nunca commitar o arquivo `.env`**
2. **Usar secrets do Docker** para informações sensíveis
3. **Manter imagens atualizadas** regularmente
4. **Usar HTTPS** em produção
5. **Configurar firewall** adequadamente
6. **Fazer backups regulares**

### Firewall (UFW)

```bash
# Permitir SSH
sudo ufw allow 22/tcp

# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Ativar firewall
sudo ufw enable
sudo ufw status
```

## 📝 Checklist de Deploy

- [ ] Docker e Docker Compose instalados
- [ ] Código do projeto no servidor
- [ ] Arquivo `.env` configurado
- [ ] Containers construídos e rodando
- [ ] Nginx configurado
- [ ] SSL configurado (Let's Encrypt)
- [ ] Firewall configurado
- [ ] Backups configurados
- [ ] Monitoramento configurado
- [ ] Testes de funcionalidade realizados

## 🆘 Suporte

Em caso de problemas:
1. Verificar logs: `docker-compose logs -f`
2. Verificar status: `docker-compose ps`
3. Verificar recursos: `docker stats`
4. Verificar conectividade: `docker network inspect`

