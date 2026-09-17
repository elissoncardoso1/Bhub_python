# 📚 BHUB Backend - Documentação Completa

> **Versão:** 1.0.0  
> **Python:** ≥3.12  
> **Framework:** FastAPI  
> **Última atualização:** Dezembro 2024

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Estrutura de Diretórios](#-estrutura-de-diretórios)
3. [Dependências](#-dependências)
4. [Configuração](#-configuração)
5. [Banco de Dados](#-banco-de-dados)
6. [API Endpoints](#-api-endpoints)
7. [Serviços](#-serviços)
8. [Middlewares e Segurança](#-middlewares-e-segurança)
9. [Machine Learning](#-machine-learning)
10. [Jobs Agendados](#-jobs-agendados)
11. [Scripts Utilitários](#-scripts-utilitários)
12. [Deploy](#-deploy)
13. [Checklist de Verificação](#-checklist-de-verificação)

---

## 🎯 Visão Geral

O **BHUB Backend** é uma API REST desenvolvida em **FastAPI** para agregação e análise de artigos científicos em Análise do Comportamento. 

### Principais Funcionalidades

- 📰 **Agregação de Feeds RSS** - Sincronização automática de artigos científicos
- 🔍 **Busca Full-Text** - Pesquisa semântica com SQLite FTS5
- 🤖 **Classificação ML** - Categorização automática via embeddings
- 📄 **Processamento de PDFs** - Extração de metadados e texto
- 🌐 **Web Scraping** - Extração de artigos de sites
- 🔒 **Autenticação JWT** - Sistema completo com refresh tokens
- 📊 **Analytics** - Métricas de uso e comportamento

---

## 📁 Estrutura de Diretórios

```
bhub-backend-python/
├── alembic/                    # Migrações de banco de dados
│   ├── env.py
│   └── versions/
│       ├── 001_add_translation_cache.py
│       └── 002_add_analytics_tables.py
│
├── app/                        # Código principal da aplicação
│   ├── __init__.py
│   ├── main.py                 # ⭐ Entry point da aplicação
│   ├── config.py               # ⭐ Configurações (pydantic-settings)
│   ├── database.py             # ⭐ Conexão SQLAlchemy async
│   │
│   ├── api/                    # Rotas da API
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependências (auth, db, etc.)
│   │   ├── auth/               # Rotas de autenticação
│   │   │   └── router.py
│   │   └── v1/                 # API v1
│   │       ├── __init__.py
│   │       ├── articles.py
│   │       ├── authors.py
│   │       ├── banners.py
│   │       ├── categories.py
│   │       ├── contact.py
│   │       ├── csrf.py
│   │       ├── feeds.py
│   │       ├── ai.py
│   │       ├── analytics.py
│   │       ├── opengraph.py
│   │       ├── search.py
│   │       └── admin/          # Rotas administrativas
│   │           ├── analytics.py
│   │           ├── articles.py
│   │           ├── feeds.py
│   │           └── stats.py
│   │
│   ├── ai/                     # Integração com IA (DeepSeek/OpenRouter)
│   │   └── manager.py
│   │
│   ├── core/                   # Utilitários core
│   │   ├── analytics_middleware.py
│   │   ├── auth_cookie_middleware.py
│   │   ├── cookie_transport.py
│   │   ├── csrf_middleware.py
│   │   ├── csrf.py
│   │   ├── exceptions.py
│   │   ├── ip_anonymization.py
│   │   ├── log_sanitizer.py
│   │   ├── logging.py          # Loguru config
│   │   ├── rate_limiting.py
│   │   ├── refresh_token.py
│   │   ├── security_headers.py
│   │   └── security.py
│   │
│   ├── jobs/                   # Jobs agendados
│   │   └── scheduler.py        # APScheduler
│   │
│   ├── ml/                     # Machine Learning
│   │   ├── embedding_classifier.py  # Classificação de artigos
│   │   └── impact_rating.py         # Score de impacto
│   │
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── analytics.py
│   │   ├── article.py
│   │   ├── author.py
│   │   ├── banner.py
│   │   ├── category.py
│   │   ├── contact.py
│   │   ├── feed.py
│   │   ├── pdf_metadata.py
│   │   ├── translation_cache.py
│   │   └── user.py
│   │
│   ├── schemas/                # Schemas Pydantic
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── article.py
│   │   ├── author.py
│   │   ├── banner.py
│   │   ├── category.py
│   │   ├── common.py
│   │   ├── feed.py
│   │   └── user.py
│   │
│   └── services/               # Serviços de negócio
│       ├── __init__.py
│       ├── analytics_service.py
│       ├── article_parser.py
│       ├── background_tasks.py
│       ├── feed_aggregator.py
│       ├── opengraph_service.py
│       ├── pdf_service.py
│       ├── search_service.py
│       ├── translation_cache_service.py
│       └── web_scraper.py
│
├── config/                     # Configurações de deploy
│   ├── env.production.template
│   ├── nginx/
│   │   └── bhub.conf
│   └── pm2/
│       └── ecosystem.config.js
│
├── docs/                       # Documentação
│   ├── VPS_DEPLOY.md
│   ├── VPS_MAINTENANCE.md
│   └── VPS_UPLOAD.md
│
├── logs/                       # Logs da aplicação
│
├── scripts/                    # Scripts utilitários
│   ├── add_journal_feeds.py
│   ├── create_superuser.py
│   ├── reprocess_authors.py
│   ├── reprocess_classification.py
│   ├── reprocess_impact_score.py
│   ├── seed_feeds.py
│   ├── sync_feeds.py
│   ├── test_deepseek.py
│   └── vps/
│       ├── backup.sh
│       ├── deploy.sh
│       ├── health-check.sh
│       ├── setup-log-rotation.sh
│       ├── setup-vps.sh
│       └── update.sh
│
├── tests/                      # Testes
│   ├── conftest.py
│   └── test_articles.py
│
├── uploads/                    # Uploads (PDFs, imagens)
│   ├── og_images/
│   └── pdfs/
│
├── .env                        # ⚠️ Variáveis de ambiente (NÃO commitar)
├── alembic.ini                 # Config Alembic
├── docker-compose.yml          # Desenvolvimento
├── docker-compose.prod.yml     # Produção
├── Dockerfile                  # Desenvolvimento
├── Dockerfile.prod             # ⚠️ LEGADO (stack da raiz, ./Frontend inexistente): a imagem do deploy usa Dockerfile — ver docs/quality/BASELINE.md §5
├── pyproject.toml              # Config do projeto
├── requirements.txt            # Dependências
└── README.md
```

---

## 📦 Dependências

### Dependências Principais (requirements.txt)

| Categoria | Pacote | Versão Mínima | Descrição |
|-----------|--------|---------------|-----------|
| **Framework Web** |
| | fastapi | ≥0.115.0 | Framework web assíncrono |
| | uvicorn[standard] | ≥0.32.0 | Servidor ASGI |
| | python-multipart | ≥0.0.12 | Upload de arquivos |
| | starlette | ≥0.41.0 | Base do FastAPI |
| **Database** |
| | sqlalchemy[asyncio] | ≥2.0.36 | ORM com suporte async |
| | aiosqlite | ≥0.20.0 | Driver SQLite async |
| | alembic | ≥1.14.0 | Migrações de banco |
| | greenlet | ≥3.1.0 | Suporte coroutines |
| **Autenticação** |
| | fastapi-users[sqlalchemy] | ≥14.0.0 | Sistema de usuários |
| | python-jose[cryptography] | ≥3.3.0 | JWT tokens |
| | passlib[bcrypt] | ≥1.7.4 | Hash de senhas |
| **Validação** |
| | pydantic | ≥2.10.0 | Validação de dados |
| | pydantic-settings | ≥2.6.0 | Configurações |
| | email-validator | ≥2.2.0 | Validação de email |
| **HTTP Client** |
| | httpx | ≥0.28.0 | Cliente HTTP async |
| | aiohttp | ≥0.11.0 | Cliente HTTP alternativo |
| **RSS/Feed Parsing** |
| | feedparser | ≥6.0.11 | Parser de feeds RSS/Atom |
| | python-dateutil | ≥2.9.0 | Parsing de datas |
| **Web Scraping** |
| | beautifulsoup4 | ≥4.12.3 | Parser HTML |
| | selectolax | ≥0.3.27 | Parser HTML rápido |
| | lxml | ≥5.3.0 | Parser XML/HTML |
| **PDF Processing** |
| | pymupdf | ≥1.24.0 | Leitura de PDFs |
| | pdfplumber | ≥0.11.0 | Extração de texto PDF |
| **Machine Learning** |
| | sentence-transformers | ≥3.3.0 | Embeddings de texto |
| | torch | ≥2.5.0 | PyTorch (backend ML) |
| | numpy | ≥2.1.0 | Computação numérica |
| | scikit-learn | ≥1.5.0 | Algoritmos ML |
| **Jobs/Scheduling** |
| | apscheduler | ≥3.10.4 | Agendamento de tarefas |
| **Logging** |
| | loguru | ≥0.7.2 | Logging avançado |
| **Image Processing** |
| | pillow | ≥11.0.0 | Manipulação de imagens |
| **Utilities** |
| | python-slugify | ≥8.0.4 | Geração de slugs |
| | tenacity | ≥9.0.0 | Retry logic |
| | aiofiles | ≥24.1.0 | I/O assíncrono |
| **Rate Limiting** |
| | slowapi | ≥0.1.9 | Rate limiting |
| **Timezone** |
| | pytz | ≥2024.2 | Fusos horários |

### Dependências de Desenvolvimento

| Pacote | Versão | Descrição |
|--------|--------|-----------|
| pytest | ≥8.3.0 | Framework de testes |
| pytest-asyncio | ≥0.24.0 | Suporte async para pytest |
| pytest-cov | ≥6.0.0 | Cobertura de código |
| httpx | ≥0.28.0 | Cliente HTTP para testes |
| ruff | ≥0.8.0 | Linter e formatter |
| mypy | ≥1.13.0 | Type checking |
| pre-commit | ≥4.0.0 | Git hooks |

---

## ⚙️ Configuração

### Variáveis de Ambiente Obrigatórias

```bash
# ============================================
# APP CONFIGURATION
# ============================================
APP_NAME=BHUB
APP_VERSION=1.0.0
DEBUG=false                    # ⚠️ DEVE ser false em produção
ENVIRONMENT=production         # development | staging | production

# ============================================
# SECURITY - CRÍTICO!
# ============================================
SECRET_KEY=                    # ⚠️ OBRIGATÓRIO: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15 # 15 minutos (tokens de curta duração)
REFRESH_TOKEN_EXPIRE_DAYS=7    # 7 dias para refresh

# ⚠️ NUNCA use wildcards (*) em produção!
ALLOWED_ORIGINS=https://seudominio.com,https://www.seudominio.com

# ============================================
# DATABASE
# ============================================
DATABASE_URL=sqlite+aiosqlite:///./bhub.db

# ============================================
# AI SERVICES (Opcionais)
# ============================================
DEEPSEEK_API_KEY=              # Para tradução e análise
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
OPENROUTER_API_KEY=            # Alternativa ao DeepSeek
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
HUGGINGFACE_API_KEY=           # Para ML adicional

# ============================================
# SCHEDULER / CRON
# ============================================
CRON_SECRET=                   # ⚠️ openssl rand -hex 16
ENABLE_SCHEDULER=true
SYNC_INTERVAL_HOURS=1

# ============================================
# SERVER
# ============================================
HOST=0.0.0.0
PORT=8000

# ============================================
# PATHS
# ============================================
UPLOAD_DIR=./uploads
LOG_DIR=./logs

# ============================================
# PDF PROCESSING
# ============================================
MAX_PDF_SIZE_MB=50
PDF_UPLOAD_SUBDIR=pdfs

# ============================================
# MACHINE LEARNING
# ============================================
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
CLASSIFICATION_THRESHOLD=0.3

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60           # segundos

# ============================================
# LOGGING
# ============================================
LOG_LEVEL=INFO
LOG_ROTATION=10 MB
LOG_RETENTION=1 month

# ============================================
# ANALYTICS
# ============================================
ENABLE_ANALYTICS=true
ANALYTICS_RESPECT_DNT=true     # Respeitar Do Not Track
```

### Validações de Produção

O sistema **automaticamente valida** em ambiente de produção:

| Validação | Descrição |
|-----------|-----------|
| `SECRET_KEY` | Deve ter ≥32 caracteres e não ser valor padrão |
| `ALLOWED_ORIGINS` | Não pode conter wildcards (*) |
| `DEBUG` | Deve ser `false` |
| Origens | Devem começar com `http://` ou `https://` |

---

## 🗄️ Banco de Dados

### Modelos SQLAlchemy

| Modelo | Tabela | Descrição |
|--------|--------|-----------|
| `User` | `users` | Usuários do sistema |
| `Category` | `categories` | Categorias de artigos |
| `Feed` | `feeds` | Feeds RSS cadastrados |
| `Article` | `articles` | Artigos agregados |
| `Author` | `authors` | Autores dos artigos |
| `Banner` | `banners` | Banners promocionais |
| `ContactMessage` | `contact_messages` | Mensagens de contato |
| `PDFMetadata` | `pdf_metadata` | Metadados de PDFs |
| `TranslationCache` | `translation_cache` | Cache de traduções |
| `AnalyticsEvent` | `analytics_events` | Eventos de analytics |
| `AnalyticsSession` | `analytics_sessions` | Sessões de usuários |
| `AnalyticsMetric` | `analytics_metrics` | Métricas agregadas |

### Relacionamentos

```
User (1) ─────── (N) Article (uploaded_by)
Category (1) ──── (N) Article
Feed (1) ──────── (N) Article
Article (N) ───── (N) Author (via article_authors)
Article (1) ───── (1) PDFMetadata
```

### Migrações Alembic

```bash
# Status das migrações
alembic current

# Aplicar migrações pendentes
alembic upgrade head

# Criar nova migração
alembic revision --autogenerate -m "descrição"

# Reverter última migração
alembic downgrade -1
```

### Migrações Existentes

| ID | Nome | Descrição |
|----|------|-----------|
| 001 | add_translation_cache | Tabela de cache de traduções |
| 002 | add_analytics_tables | Tabelas de analytics |

### Busca Full-Text (FTS5)

O sistema cria automaticamente uma tabela virtual FTS5:

```sql
CREATE VIRTUAL TABLE articles_fts USING fts5(
    title,
    abstract,
    keywords,
    content='articles',
    content_rowid='id'
)
```

Com triggers para manter sincronizado com a tabela `articles`.

---

## 🌐 API Endpoints

### Rotas Públicas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| **Artigos** |
| GET | `/api/v1/articles` | Listar artigos (paginado) |
| GET | `/api/v1/articles/{id}` | Detalhes do artigo |
| GET | `/api/v1/articles/{id}/similar` | Artigos similares |
| GET | `/api/v1/articles/feed/{feed_id}` | Artigos por feed |
| **Autores** |
| GET | `/api/v1/authors` | Listar autores |
| GET | `/api/v1/authors/{id}` | Detalhes do autor |
| **Categorias** |
| GET | `/api/v1/categories` | Listar categorias |
| GET | `/api/v1/categories/{id}` | Detalhes da categoria |
| **Feeds** |
| GET | `/api/v1/feeds` | Listar feeds |
| GET | `/api/v1/feeds/{id}` | Detalhes do feed |
| **Busca** |
| GET | `/api/v1/search` | Busca de artigos |
| GET | `/api/v1/search/suggestions` | Sugestões de busca |
| **Banners** |
| GET | `/api/v1/banners` | Listar banners ativos |
| POST | `/api/v1/banners/{id}/click` | Registrar clique |
| **Contato** |
| POST | `/api/v1/contact` | Enviar mensagem |
| **AI** |
| POST | `/api/v1/ai/translate` | Traduzir texto |
| POST | `/api/v1/ai/summarize` | Resumir texto |
| **Analytics** |
| POST | `/api/v1/analytics/event` | Registrar evento |
| **OpenGraph** |
| GET | `/api/v1/opengraph/{article_id}` | Imagem OG do artigo |
| **CSRF** |
| GET | `/api/v1/csrf/token` | Obter token CSRF |
| **Utilitários** |
| GET | `/` | Info da API |
| GET | `/health` | Health check |

### Rotas de Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/auth/jwt/login` | Login (retorna JWT) |
| POST | `/auth/jwt/logout` | Logout |
| POST | `/auth/jwt/refresh` | Refresh token |
| POST | `/auth/register` | Criar conta |
| POST | `/auth/verify` | Verificar email |
| POST | `/auth/forgot-password` | Recuperar senha |
| POST | `/auth/reset-password` | Resetar senha |

### Rotas Admin (Requer Autenticação)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| **Admin Stats** |
| GET | `/api/v1/admin/stats` | Estatísticas gerais |
| GET | `/api/v1/admin/stats/recent` | Atividade recente |
| **Admin Articles** |
| POST | `/api/v1/admin/articles` | Criar artigo |
| PATCH | `/api/v1/admin/articles/{id}` | Atualizar artigo |
| DELETE | `/api/v1/admin/articles/{id}` | Excluir artigo |
| POST | `/api/v1/admin/articles/highlight` | Destacar artigo |
| POST | `/api/v1/admin/articles/scrape` | Importar via scraping |
| POST | `/api/v1/admin/articles/upload-pdf` | Upload de PDF |
| **Admin Feeds** |
| POST | `/api/v1/admin/feeds` | Criar feed |
| PATCH | `/api/v1/admin/feeds/{id}` | Atualizar feed |
| DELETE | `/api/v1/admin/feeds/{id}` | Excluir feed |
| POST | `/api/v1/admin/feeds/{id}/sync` | Sincronizar feed |
| POST | `/api/v1/admin/feeds/sync-all` | Sincronizar todos |
| POST | `/api/v1/admin/feeds/test` | Testar URL do feed |
| **Admin Analytics** |
| GET | `/api/v1/admin/analytics/overview` | Overview de analytics |
| GET | `/api/v1/admin/analytics/traffic` | Estatísticas de tráfego |
| GET | `/api/v1/admin/analytics/content` | Estatísticas de conteúdo |
| GET | `/api/v1/admin/analytics/events` | Estatísticas de eventos |

### Rota Cron (Interna)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/cron/sync` | Sincronização via cron externo |

---

## 🔧 Serviços

| Serviço | Arquivo | Descrição |
|---------|---------|-----------|
| `FeedAggregatorService` | `feed_aggregator.py` | Sincronização de feeds RSS |
| `ArticleParserService` | `article_parser.py` | Parsing de artigos |
| `WebScrapingService` | `web_scraper.py` | Web scraping de artigos |
| `PDFService` | `pdf_service.py` | Processamento de PDFs |
| `SearchService` | `search_service.py` | Busca full-text |
| `OpenGraphService` | `opengraph_service.py` | Geração de imagens OG |
| `TranslationCacheService` | `translation_cache_service.py` | Cache de traduções |
| `AnalyticsService` | `analytics_service.py` | Processamento de analytics |

---

## 🛡️ Middlewares e Segurança

### Middlewares Ativos

| Middleware | Descrição |
|------------|-----------|
| `SecurityHeadersMiddleware` | Headers de segurança HTTP |
| `CSRFMiddleware` | Proteção CSRF |
| `AuthCookieMiddleware` | Cookies HttpOnly para tokens |
| `AnalyticsMiddleware` | Rastreamento de analytics |
| `CORSMiddleware` | Controle de CORS |

### Headers de Segurança

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: ...
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Rate Limiting

- **API:** 10 requests/segundo por IP
- **Geral:** 30 requests/segundo por IP
- **Cron endpoint:** 3 requests/hora

---

## 🤖 Machine Learning

### EmbeddingClassifier

- **Modelo:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Função:** Classificação automática de artigos em categorias
- **Threshold:** 0.3 (similaridade mínima)

### Impact Rating

- **Função:** Cálculo de score de impacto dos artigos
- **Fatores:** Citações, fator de impacto do journal, recência

---

## ⏰ Jobs Agendados

| Job | Schedule | Descrição |
|-----|----------|-----------|
| `sync_all_feeds_job` | A cada hora (minuto 0) | Sincroniza todos os feeds RSS ativos |

### Configuração do Scheduler

```python
# app/jobs/scheduler.py
scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Sao_Paulo"))
```

---

## 📜 Scripts Utilitários

| Script | Descrição | Uso |
|--------|-----------|-----|
| `create_superuser.py` | Criar usuário admin | `python -m scripts.create_superuser` |
| `seed_feeds.py` | Popular feeds iniciais | `python -m scripts.seed_feeds` |
| `sync_feeds.py` | Sincronização manual | `python -m scripts.sync_feeds` |
| `add_journal_feeds.py` | Adicionar feeds de journals | `python -m scripts.add_journal_feeds` |
| `reprocess_authors.py` | Reprocessar autores | `python -m scripts.reprocess_authors` |
| `reprocess_classification.py` | Reclassificar artigos | `python -m scripts.reprocess_classification` |
| `reprocess_impact_score.py` | Recalcular scores | `python -m scripts.reprocess_impact_score` |
| `test_deepseek.py` | Testar API DeepSeek | `python -m scripts.test_deepseek` |

### Scripts VPS

| Script | Descrição |
|--------|-----------|
| `setup-vps.sh` | Setup inicial da VPS |
| `deploy.sh` | Deploy da aplicação |
| `update.sh` | Atualização da aplicação |
| `backup.sh` | Backup do banco de dados |
| `health-check.sh` | Verificar saúde dos serviços |
| `setup-log-rotation.sh` | Configurar rotação de logs |

---

## 🚀 Deploy

### Docker (Produção)

```bash
# Build e iniciar
docker-compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Parar
docker-compose -f docker-compose.prod.yml down
```

### Estrutura em Produção

```
/var/www/bhub/
├── backend/
│   └── bhub-backend-python/
│       ├── .env              # ⚠️ Configurar!
│       ├── bhub.db           # Banco SQLite
│       ├── uploads/          # Arquivos uploadados
│       └── logs/             # Logs da aplicação
├── frontend/
│   ├── .next/
│   └── .env.local
├── backups/                  # Backups automáticos
└── logs/                     # Logs gerais
```

### Nginx

Configuração em `config/nginx/bhub.conf`:

- Proxy reverso para backend (porta 8000) e frontend (porta 3000)
- SSL/TLS com Let's Encrypt
- Rate limiting
- Gzip compression
- Security headers
- Bloqueio de arquivos sensíveis

### PM2 (Frontend)

```bash
# Iniciar
pm2 start config/pm2/ecosystem.config.js

# Status
pm2 status

# Logs
pm2 logs bhub-frontend

# Reiniciar
pm2 restart bhub-frontend
```

---

## ✅ Checklist de Verificação do Deploy

### Configuração

- [ ] Arquivo `.env` criado e configurado
- [ ] `SECRET_KEY` gerado com `openssl rand -hex 32`
- [ ] `CRON_SECRET` gerado com `openssl rand -hex 16`
- [ ] `ALLOWED_ORIGINS` configurado com domínios corretos (sem wildcards)
- [ ] `DEBUG=false`
- [ ] `ENVIRONMENT=production`
- [ ] Chaves de API configuradas (DEEPSEEK, OPENROUTER, etc.)

### Banco de Dados

- [ ] Arquivo `bhub.db` existe e tem permissões corretas
- [ ] Migrações aplicadas (`alembic upgrade head`)
- [ ] Categorias padrão criadas (automático no startup)
- [ ] Superuser criado (`python -m scripts.create_superuser`)
- [ ] Feeds iniciais cadastrados (`python -m scripts.seed_feeds`)

### Diretórios

- [ ] `uploads/` existe com permissões de escrita
- [ ] `uploads/pdfs/` existe
- [ ] `uploads/og_images/` existe
- [ ] `logs/` existe com permissões de escrita

### Docker

- [ ] `docker-compose.prod.yml` configurado
- [ ] Container `bhub-backend` rodando
- [ ] Health check passando (`curl http://localhost:8000/health`)
- [ ] Logs sem erros (`docker-compose logs`)

### Nginx

- [ ] Configuração em `/etc/nginx/sites-available/bhub`
- [ ] Link simbólico em `/etc/nginx/sites-enabled/`
- [ ] Domínio substituído na configuração
- [ ] `nginx -t` passa sem erros
- [ ] Nginx recarregado (`systemctl reload nginx`)

### SSL/HTTPS

- [ ] Certificado Let's Encrypt instalado
- [ ] Renovação automática configurada
- [ ] HSTS ativo
- [ ] Redirect HTTP → HTTPS funcionando

### Firewall

- [ ] UFW ativo
- [ ] Portas 22 (SSH), 80 (HTTP), 443 (HTTPS) liberadas
- [ ] Portas 8000 e 3000 bloqueadas externamente

### Scheduler

- [ ] `ENABLE_SCHEDULER=true` configurado
- [ ] Job de sincronização rodando (verificar logs)
- [ ] Timezone correto (`America/Sao_Paulo`)

### Segurança

- [ ] Headers de segurança configurados
- [ ] CORS configurado corretamente
- [ ] CSRF ativo
- [ ] Rate limiting funcionando
- [ ] Fail2ban configurado

### Monitoramento

- [ ] Logs sendo gerados em `logs/`
- [ ] Rotação de logs configurada
- [ ] Backups automáticos configurados
- [ ] Health check acessível

### Testes Finais

```bash
# Health check
curl https://seudominio.com/health

# API funcionando
curl https://seudominio.com/api/v1/articles

# Categorias
curl https://seudominio.com/api/v1/categories

# SSL OK
curl -I https://seudominio.com

# Security headers
curl -I https://seudominio.com | grep -E "Strict|X-Frame|X-Content|X-XSS"
```

---

## 🔗 Links Úteis

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

## 📞 Suporte

Em caso de problemas:

1. Verificar logs: `docker-compose logs -f` / `pm2 logs`
2. Verificar health: `curl http://localhost:8000/health`
3. Verificar `.env` e configurações
4. Consultar documentação em `docs/`

---

**BHUB Backend** © 2024 - Desenvolvido com ❤️ para a comunidade de Análise do Comportamento

