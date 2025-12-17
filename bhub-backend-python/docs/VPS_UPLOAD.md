# Guia de Upload para VPS - BHUB

Este guia explica as diferentes formas de fazer upload do projeto BHUB para sua VPS.

## Opção 1: Usando Git (Recomendado)

A forma mais simples e recomendada é usar Git diretamente na VPS.

### Passo 1: Preparar Repositório

Se ainda não tem o código em um repositório Git:

```bash
# No seu computador local
cd /Volumes/ElissonSSD2/Projetos/Bhub_py/bhub-backend-python

# Inicializar repositório (se ainda não tiver)
git init
git add .
git commit -m "Initial commit - BHUB production ready"

# Adicionar repositório remoto (GitHub, GitLab, etc.)
git remote add origin https://github.com/seu-usuario/bhub-backend-python.git
git push -u origin main
```

### Passo 2: Clonar na VPS

```bash
# Conectar na VPS via SSH
ssh usuario@seu-ip-vps

# Criar diretório
sudo mkdir -p /var/www/bhub
sudo chown -R $USER:$USER /var/www/bhub
cd /var/www/bhub

# Clonar repositório
git clone https://github.com/seu-usuario/bhub-backend-python.git backend
cd backend

# Se usar repositório privado, configure SSH keys:
# ssh-keygen -t ed25519 -C "vps@bhub"
# cat ~/.ssh/id_ed25519.pub
# Adicione a chave pública no GitHub/GitLab
```

## Opção 2: Usando SCP (Secure Copy)

Ideal para upload direto sem Git.

### Upload do Backend

```bash
# No seu computador local (Mac/Linux)
cd /Volumes/ElissonSSD2/Projetos/Bhub_py

# Upload do backend
scp -r bhub-backend-python usuario@seu-ip-vps:/var/www/bhub/backend

# Se precisar de sudo, faça em duas etapas:
scp -r bhub-backend-python usuario@seu-ip-vps:~/
# Depois na VPS:
ssh usuario@seu-ip-vps
sudo mv ~/bhub-backend-python /var/www/bhub/backend
```

### Upload do Frontend

```bash
# Upload do frontend
scp -r Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6 usuario@seu-ip-vps:/var/www/bhub/frontend
```

### Com porta customizada

```bash
scp -P 2222 -r bhub-backend-python usuario@seu-ip-vps:/var/www/bhub/backend
```

## Opção 3: Usando rsync (Recomendado para atualizações)

Mais eficiente para atualizações futuras, sincroniza apenas arquivos alterados.

### Primeira vez (upload completo)

```bash
# No seu computador local
cd /Volumes/ElissonSSD2/Projetos/Bhub_py

# Backend
rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'bhub.db' \
  --exclude 'bhub.db-*' \
  --exclude 'uploads/' \
  --exclude 'logs/' \
  bhub-backend-python/ usuario@seu-ip-vps:/var/www/bhub/backend/

# Frontend
rsync -avz --progress \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '.env.local' \
  Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6/ usuario@seu-ip-vps:/var/www/bhub/frontend/
```

### Atualizações futuras

```bash
# Apenas sincroniza arquivos alterados
rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '.env' \
  bhub-backend-python/ usuario@seu-ip-vps:/var/www/bhub/backend/
```

## Opção 4: Usando SFTP (FileZilla, Cyberduck, etc.)

Para quem prefere interface gráfica.

### Configuração

1. **Host**: IP da sua VPS
2. **Port**: 22 (padrão SSH)
3. **Protocol**: SFTP
4. **User**: seu usuário na VPS
5. **Password**: sua senha (ou use chave SSH)

### Diretórios de destino

- Backend: `/var/www/bhub/backend/`
- Frontend: `/var/www/bhub/frontend/`

### Arquivos a NÃO enviar

- `.env` (criar na VPS)
- `bhub.db` (será criado na VPS)
- `node_modules/` (instalar na VPS)
- `.next/` (build na VPS)
- `__pycache__/`
- `.git/` (opcional)

## Opção 5: Usando TAR + SCP (Para grandes projetos)

Útil quando há muitos arquivos pequenos.

### Criar arquivo compactado

```bash
# No seu computador local
cd /Volumes/ElissonSSD2/Projetos/Bhub_py

# Backend
tar -czf bhub-backend.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='bhub.db*' \
  --exclude='uploads' \
  --exclude='logs' \
  bhub-backend-python/

# Frontend
tar -czf bhub-frontend.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='.env.local' \
  Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6/
```

### Upload e extrair

```bash
# Upload
scp bhub-backend.tar.gz usuario@seu-ip-vps:~/
scp bhub-frontend.tar.gz usuario@seu-ip-vps:~/

# Na VPS
ssh usuario@seu-ip-vps
sudo mkdir -p /var/www/bhub
sudo tar -xzf ~/bhub-backend.tar.gz -C /var/www/bhub/
sudo mv /var/www/bhub/bhub-backend-python /var/www/bhub/backend
sudo tar -xzf ~/bhub-frontend.tar.gz -C /var/www/bhub/
sudo mv /var/www/bhub/workspace-* /var/www/bhub/frontend
rm ~/bhub-*.tar.gz
```

## Script Automatizado de Upload

Crie um script para facilitar:

```bash
# Criar script: upload-to-vps.sh
#!/bin/bash

VPS_USER="usuario"
VPS_HOST="seu-ip-vps"
VPS_PATH="/var/www/bhub"

echo "Fazendo upload do backend..."
rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'bhub.db*' \
  --exclude 'uploads/' \
  --exclude 'logs/' \
  bhub-backend-python/ ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/backend/

echo "Fazendo upload do frontend..."
rsync -avz --progress \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '.env.local' \
  Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6/ ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/frontend/

echo "Upload concluído!"
```

Tornar executável:
```bash
chmod +x upload-to-vps.sh
./upload-to-vps.sh
```

## Configurar Permissões na VPS

Após o upload, configure as permissões:

```bash
# Na VPS
sudo chown -R www-data:www-data /var/www/bhub
sudo chmod -R 755 /var/www/bhub

# Diretórios que precisam de escrita
sudo chmod -R 775 /var/www/bhub/backend/uploads
sudo chmod -R 775 /var/www/bhub/backend/logs
```

## Verificação Pós-Upload

```bash
# Na VPS, verificar estrutura
ls -la /var/www/bhub/
ls -la /var/www/bhub/backend/
ls -la /var/www/bhub/frontend/

# Verificar se arquivos importantes estão presentes
ls -la /var/www/bhub/backend/scripts/vps/
ls -la /var/www/bhub/backend/config/nginx/
ls -la /var/www/bhub/backend/docker-compose.prod.yml
```

## Próximos Passos Após Upload

1. **Configurar variáveis de ambiente**:
   ```bash
   cd /var/www/bhub/backend
   cp config/env.production.template .env
   nano .env
   ```

2. **Executar setup da VPS**:
   ```bash
   sudo bash scripts/vps/setup-vps.sh
   ```

3. **Fazer deploy**:
   ```bash
   DOMAIN=seudominio.com bash scripts/vps/deploy.sh
   ```

## Dicas de Segurança

1. **Use chaves SSH** em vez de senhas:
   ```bash
   ssh-keygen -t ed25519
   ssh-copy-id usuario@seu-ip-vps
   ```

2. **Não faça upload de arquivos sensíveis**:
   - `.env`
   - Chaves privadas
   - Credenciais

3. **Use `.gitignore`** adequado:
   ```
   .env
   *.db
   *.db-*
   __pycache__/
   node_modules/
   .next/
   ```

## Troubleshooting

### Erro de permissão negada

```bash
# Verificar permissões do diretório na VPS
ls -ld /var/www/bhub

# Corrigir
sudo chown -R $USER:$USER /var/www/bhub
```

### Conexão SSH recusada

```bash
# Verificar se SSH está rodando na VPS
# Verificar firewall
sudo ufw status

# Permitir SSH
sudo ufw allow 22/tcp
```

### Upload muito lento

- Use `rsync` com compressão (`-z`)
- Use conexão via cabo (não WiFi)
- Considere usar Git para atualizações futuras

