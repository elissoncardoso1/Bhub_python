# BHUB Backend - Python

Backend da plataforma BHUB (Behavior Hub) para agregação e análise de artigos científicos em Análise do Comportamento.

## 🚀 Stack Tecnológica

- **Framework**: FastAPI 0.115+
- **Python**: 3.12+
- **ORM**: SQLAlchemy 2.0 (async)
- **Banco de Dados**: PostgreSQL 16 (produção) — SQLite somente em desenvolvimento e na suíte unitária
- **Busca Full-Text**: PostgreSQL `TSVECTOR` + `pg_trgm` (produção); FTS5 do SQLite apenas em dev
- **Autenticação**: FastAPI-Users com JWT
- **ML**: sentence-transformers
- **Scheduler**: APScheduler

## 📋 Pré-requisitos

- Python 3.12+
- pip ou uv

## 🔧 Instalação

### 1. Clonar repositório

```bash
git clone https://github.com/elissoncardoso1/Bhub_python.git
cd Bhub_python/bhub-backend-python   # a aplicação vive neste subdiretório
```

### 2. Criar ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 5. Executar migrações

```bash
alembic upgrade head
```

### 6. Iniciar servidor

```bash
uvicorn app.main:app --reload
```

O servidor estará disponível em: http://localhost:8000

## 📚 Documentação da API

- **Swagger UI**: http://localhost:8000/docs — **só existe com `DEBUG=true`** (`docs_url`/`redoc_url` são `None` fora disso: `bhub-backend-python/app/main.py:127-128`)
- **ReDoc**: http://localhost:8000/redoc — mesma condição

## 🖥️ Frontend (HTMX)

O frontend agora é servido pelo próprio FastAPI (SSR + HTMX):

- **Home / Artigos**: `GET /`
- **Detalhe do artigo**: `GET /articles/{id}`
- **Categorias**: `GET /categories`
- **Contato**: `GET /contact`
- **Admin**: `GET /admin` (requer usuário `ADMIN`)
- **Login**: `GET/POST /login`

## 🏗️ Estrutura do Projeto

```
app/
├── api/              # Rotas da API
│   ├── v1/           # Versão 1 da API
│   │   ├── admin/    # Rotas administrativas
│   │   ├── articles.py
│   │   ├── categories.py
│   │   └── ...
│   └── auth/         # Autenticação
├── models/           # Modelos SQLAlchemy
├── schemas/          # Schemas Pydantic
├── services/         # Lógica de negócio
├── ml/               # Machine Learning
├── ai/               # Integrações de IA
├── jobs/             # Jobs agendados
├── core/             # Utilitários core
└── main.py           # Aplicação principal
```

## 🔐 Autenticação

O sistema usa JWT para autenticação. Para obter um token:

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@bhub.com.br&password=sua-senha"

# Usar token
curl -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "Authorization: Bearer seu-token-jwt"
```

## 📡 Principais Endpoints

### Públicos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/articles` | Lista artigos |
| GET | `/api/v1/articles/highlighted` | Artigos destacados |
| GET | `/api/v1/categories` | Lista categorias |
| GET | `/api/v1/search/suggestions` | Sugestões de busca |
| POST | `/api/v1/contact` | Enviar mensagem |

### Admin (Requer Autenticação)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/admin/stats` | Estatísticas |
| POST | `/api/v1/admin/feeds` | Criar feed |
| POST | `/api/v1/admin/feeds/sync-all` | Sincronizar feeds |
| POST | `/api/v1/admin/articles/upload-pdf` | Upload de PDF |
| POST | `/api/v1/admin/articles/scrape` | Scraping de URL |

### IA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ai/classify` | Classificar texto |
| POST | `/api/v1/ai/translate` | Traduzir texto |
| GET | `/api/v1/ai/status` | Status dos provedores |

## 🐳 Docker

```bash
# Produção — de DENTRO de bhub-backend-python/ (é o compose com PostgreSQL + Redis + arq-worker)
cd bhub-backend-python && docker compose -f docker-compose.prod.yml up -d

# Desenvolvimento
cd bhub-backend-python && docker compose up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f backend
```

## 🧪 Testes

```bash
# Executar testes
pytest tests/ -v

# Com cobertura
pytest tests/ -v --cov=app --cov-report=html
```

## 📦 Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL do banco | `postgresql+asyncpg://bhub:bhub@db:5432/bhub` nos dois composes de `bhub-backend-python/` (`docker-compose.yml:15`, `docker-compose.prod.yml:32`); o default da aplicação, usado em dev/testes, é `sqlite+aiosqlite:///./bhub.db`. **Exceção legada, não é caminho de deploy:** o `docker-compose.prod.yml` da **raiz** ainda fixa SQLite (`:31`) e monta um `./Frontend` que não existe no repositório (registrado em ADR-0001 e em `docs/quality/BASELINE.md`) |
| `SECRET_KEY` | Chave JWT | - |
| `DEBUG` | Modo debug | `false` |
| `DEEPSEEK_API_KEY` | API DeepSeek | - |
| `OPENROUTER_API_KEY` | API OpenRouter | - |
| `ENABLE_SCHEDULER` | Habilitar jobs | `true` |

## 🔄 Migrações

```bash
# Criar nova migração
alembic revision --autogenerate -m "Descrição"

# Aplicar migrações
alembic upgrade head

# Reverter última
alembic downgrade -1
```

## 📊 Machine Learning

O sistema usa `sentence-transformers` para classificação automática de artigos:

- **Modelo**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Funcionalidades**:
  - Classificação automática em categorias
  - Avaliação de impacto de artigos
  - Busca semântica (futuro)

## 🛡️ Segurança

- Autenticação JWT com tokens seguros
- Rate limiting para proteção contra abuse
- Validação de uploads (tipo, tamanho, estrutura)
- Sanitização de inputs
- Headers de segurança configurados

## 📈 Monitoramento

- Health check: `GET /health`
- Logs estruturados com Loguru
- Estatísticas em `/api/v1/admin/stats`

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 👥 Equipe

Desenvolvido pela equipe BHUB.
