# 🐳 BHUB - Deploy com Docker

Este projeto está configurado para rodar completamente em containers Docker.

## 📦 Estrutura Docker

```
Bhub_py/
├── docker-compose.prod.yml    # Orquestração completa (backend + frontend)
├── deploy-docker.sh            # Script de deploy automatizado
├── .env.example               # Template de variáveis de ambiente
├── bhub-backend-python/
│   ├── Dockerfile.prod        # Dockerfile do backend
│   └── docker-compose.prod.yml # Docker Compose do backend (standalone)
└── Frontend/
    ├── Dockerfile              # Dockerfile do frontend
    └── .dockerignore           # Arquivos ignorados no build
```

## 🚀 Deploy Rápido

### 1. Preparar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar e configurar
nano .env
```

### 2. Executar Deploy

```bash
# Deploy completo (primeira vez)
./deploy-docker.sh --build

# Deploy com restart
./deploy-docker.sh --restart

# Deploy simples (sem rebuild)
./deploy-docker.sh
```

### 3. Verificar Status

```bash
# Ver containers
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 📋 Serviços

### Backend
- **Container**: `bhub-backend`
- **Porta interna**: `8000`
- **Health check**: `http://localhost:8000/health`

### Frontend
- **Container**: `bhub-frontend`
- **Porta interna**: `3000`
- **Health check**: `http://localhost:3000`

## 🔧 Comandos Úteis

```bash
# Iniciar
docker-compose -f docker-compose.prod.yml up -d

# Parar
docker-compose -f docker-compose.prod.yml down

# Reconstruir
docker-compose -f docker-compose.prod.yml build --no-cache

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f [servico]

# Reiniciar
docker-compose -f docker-compose.prod.yml restart

# Executar comando no container
docker exec -it bhub-backend bash
docker exec -it bhub-frontend sh
```

## 🌐 Configuração Nginx

Após iniciar os containers, configure o Nginx como reverse proxy:

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
}
```

## 📝 Variáveis de Ambiente Importantes

- `SECRET_KEY`: Chave secreta do backend (gerar com `openssl rand -hex 32`)
- `ALLOWED_ORIGINS`: Origens permitidas (separar por vírgula)
- `NEXT_PUBLIC_API_URL`: URL pública da API
- `BACKEND_URL`: URL do backend para Next.js rewrites (usar `http://backend:8000` no Docker)

## 🔍 Troubleshooting

### Build falha
```bash
# Limpar cache e reconstruir
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Containers não iniciam
```bash
# Ver logs detalhados
docker-compose -f docker-compose.prod.yml logs

# Verificar recursos
docker stats
```

### Frontend não conecta ao backend
- Verificar se `BACKEND_URL` está configurado corretamente
- Verificar se ambos containers estão na mesma rede Docker
- Verificar logs: `docker-compose logs frontend`

## 📚 Documentação Completa

Veja `DOCKER_DEPLOY.md` para documentação completa de deploy em produção.
