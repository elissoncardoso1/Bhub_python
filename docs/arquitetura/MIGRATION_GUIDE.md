# Guia de Migração: BHUB Backend - Next.js para Python

## Visão Geral da Migração

Este documento detalha a migração completa do backend BHUB de Next.js/TypeScript para Python, utilizando FastAPI como framework principal.

## Stack Tecnológica Python

| Componente Original (Next.js) | Equivalente Python |
|-------------------------------|-------------------|
| Next.js 16 (App Router) | **FastAPI 0.115+** |
| TypeScript | **Python 3.12+** com Type Hints |
| Prisma ORM | **SQLAlchemy 2.0** + Alembic |
| SQLite | **SQLite** (via aiosqlite) |
| NextAuth (JWT) | **FastAPI-Users** + python-jose |
| @xenova/transformers | **sentence-transformers** |
| rss-parser | **feedparser** |
| axios + cheerio | **httpx** + **beautifulsoup4** + **selectolax** |
| pdf-parse | **PyMuPDF (fitz)** + **pdfplumber** |
| node-cron | **APScheduler** ou **Celery** |
| Winston logger | **loguru** |
| bcrypt | **passlib[bcrypt]** |

## Estrutura do Projeto

```
bhub-backend-python/
├── alembic/                    # Migrações de banco de dados
│   ├── versions/
│   └── env.py
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicação FastAPI principal
│   ├── config.py               # Configurações e variáveis de ambiente
│   ├── database.py             # Configuração do SQLAlchemy
│   │
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── article.py
│   │   ├── feed.py
│   │   ├── category.py
│   │   ├── author.py
│   │   ├── banner.py
│   │   ├── contact.py
│   │   └── pdf_metadata.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── article.py
│   │   ├── feed.py
│   │   ├── category.py
│   │   ├── banner.py
│   │   └── common.py
│   │
│   ├── api/                    # Rotas da API
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependências comuns
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── articles.py
│   │   │   ├── feeds.py
│   │   │   ├── search.py
│   │   │   ├── banners.py
│   │   │   ├── contact.py
│   │   │   ├── ai.py
│   │   │   └── admin/
│   │   │       ├── __init__.py
│   │   │       ├── articles.py
│   │   │       ├── feeds.py
│   │   │       ├── banners.py
│   │   │       ├── messages.py
│   │   │       └── stats.py
│   │   └── auth/
│   │       ├── __init__.py
│   │       └── routes.py
│   │
│   ├── services/               # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── feed_aggregator.py
│   │   ├── article_parser.py
│   │   ├── web_scraper.py
│   │   ├── pdf_service.py
│   │   ├── search_service.py
│   │   ├── image_extractor.py
│   │   └── stats_service.py
│   │
│   ├── ml/                     # Machine Learning
│   │   ├── __init__.py
│   │   ├── embedding_classifier.py
│   │   ├── impact_rating.py
│   │   └── setup_embeddings.py
│   │
│   ├── ai/                     # Integrações de IA externa
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── deepseek.py
│   │   ├── openrouter.py
│   │   └── huggingface.py
│   │
│   ├── translation/            # Sistema de tradução
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── ai_translation.py
│   │   ├── professional.py
│   │   └── aba_glossary.py
│   │
│   ├── jobs/                   # Jobs agendados
│   │   ├── __init__.py
│   │   ├── scheduler.py
│   │   └── tasks.py
│   │
│   ├── core/                   # Utilitários core
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   └── utils/                  # Utilitários gerais
│       ├── __init__.py
│       ├── og_image.py
│       └── helpers.py
│
├── uploads/                    # Diretório de uploads
│   └── pdfs/
├── logs/                       # Logs da aplicação
├── tests/                      # Testes
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_articles.py
│   └── test_feeds.py
├── scripts/                    # Scripts utilitários
│   ├── init_db.py
│   └── seed_categories.py
├── .env.example
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Dependências Principais

```toml
# pyproject.toml
[project]
name = "bhub-backend"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    # Framework Web
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-multipart>=0.0.12",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "aiosqlite>=0.20.0",
    "alembic>=1.14.0",
    
    # Autenticação
    "fastapi-users[sqlalchemy]>=14.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # Validação
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "email-validator>=2.2.0",
    
    # HTTP Client
    "httpx>=0.28.0",
    "aiohttp>=3.11.0",
    
    # RSS/Feed Parsing
    "feedparser>=6.0.11",
    "python-dateutil>=2.9.0",
    
    # Web Scraping
    "beautifulsoup4>=4.12.3",
    "selectolax>=0.3.27",
    "lxml>=5.3.0",
    
    # PDF Processing
    "pymupdf>=1.24.0",
    "pdfplumber>=0.11.0",
    
    # Machine Learning
    "sentence-transformers>=3.3.0",
    "torch>=2.5.0",
    "numpy>=2.1.0",
    
    # Jobs/Scheduling
    "apscheduler>=3.10.4",
    
    # Logging
    "loguru>=0.7.2",
    
    # Image Processing
    "pillow>=11.0.0",
    
    # Utilities
    "python-slugify>=8.0.4",
    "tenacity>=9.0.0",
    
    # Full-text Search
    "sqlite-fts4>=1.0.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]
```

## Mapeamento de Funcionalidades

### 1. Sistema de Autenticação

**Original (NextAuth):**
```typescript
// src/lib/auth.config.ts
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      credentials: { email, password },
      async authorize(credentials) { ... }
    })
  ],
  session: { strategy: "jwt" }
}
```

**Python (FastAPI-Users):**
```python
# app/core/security.py
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600*24)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)
```

### 2. Sistema de Feed RSS

**Original (rss-parser):**
```typescript
// src/lib/rss/FeedAggregatorService.ts
import Parser from 'rss-parser';
const parser = new Parser();
const feed = await parser.parseURL(feedUrl);
```

**Python (feedparser):**
```python
# app/services/feed_aggregator.py
import feedparser
import httpx

async def parse_feed(feed_url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(feed_url)
    return feedparser.parse(response.text)
```

### 3. Sistema de Web Scraping

**Original (axios + cheerio):**
```typescript
// src/lib/scraping/WebScrapingService.ts
import axios from 'axios';
import * as cheerio from 'cheerio';
const $ = cheerio.load(html);
const title = $('h1.article-title').text();
```

**Python (httpx + beautifulsoup4):**
```python
# app/services/web_scraper.py
import httpx
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser  # Mais rápido para parsing simples

async def scrape_article(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=BROWSER_HEADERS)
    soup = BeautifulSoup(response.text, 'lxml')
    title = soup.select_one('h1.article-title').get_text(strip=True)
    return {"title": title, ...}
```

### 4. Sistema de PDF

**Original (pdf-parse):**
```typescript
// src/lib/pdf/PDFParserService.ts
import pdfParse from 'pdf-parse';
const data = await pdfParse(buffer);
const text = data.text;
```

**Python (PyMuPDF + pdfplumber):**
```python
# app/services/pdf_service.py
import fitz  # PyMuPDF
import pdfplumber

def extract_text_pymupdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_pdfplumber(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text
```

### 5. Sistema de ML/Embeddings

**Original (@xenova/transformers):**
```typescript
// src/lib/ml/embedClassifier.ts
import { pipeline } from '@xenova/transformers';
const extractor = await pipeline('feature-extraction', 
    'Xenova/paraphrase-multilingual-MiniLM-L12-v2');
const embeddings = await extractor(text, { pooling: 'mean' });
```

**Python (sentence-transformers):**
```python
# app/ml/embedding_classifier.py
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingClassifier:
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.category_embeddings = {}
    
    def classify(self, text: str) -> tuple[str, float]:
        embedding = self.model.encode(text)
        similarities = {
            cat: np.dot(embedding, cat_emb) / (np.linalg.norm(embedding) * np.linalg.norm(cat_emb))
            for cat, cat_emb in self.category_embeddings.items()
        }
        best_category = max(similarities, key=similarities.get)
        return best_category, similarities[best_category]
```

### 6. Sistema de Busca FTS5

**Original:**
```typescript
// src/lib/search/fts5Search.ts
const results = await prisma.$queryRaw`
    SELECT rowid, bm25(articles_fts) as rank
    FROM articles_fts
    WHERE articles_fts MATCH ${query}
    ORDER BY rank
`;
```

**Python (SQLAlchemy + FTS5):**
```python
# app/services/search_service.py
from sqlalchemy import text

async def search_fts5(db: AsyncSession, query: str) -> list[int]:
    result = await db.execute(
        text("""
            SELECT rowid, bm25(articles_fts) as rank
            FROM articles_fts
            WHERE articles_fts MATCH :query
            ORDER BY rank
        """),
        {"query": query}
    )
    return [row.rowid for row in result.fetchall()]
```

### 7. Sistema de Jobs/Cron

**Original (node-cron):**
```typescript
// src/jobs/cron.ts
import cron from 'node-cron';
cron.schedule('0 * * * *', async () => {
    await syncAllFeeds();
}, { timezone: "America/Sao_Paulo" });
```

**Python (APScheduler):**
```python
# app/jobs/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Sao_Paulo"))

@scheduler.scheduled_job(CronTrigger(minute=0))  # A cada hora
async def sync_all_feeds():
    await feed_service.sync_all_active_feeds()

def start_scheduler():
    scheduler.start()
```

## Rotas da API - Mapeamento

### Rotas Públicas

| Original | Python FastAPI |
|----------|---------------|
| `GET /api/articles` | `GET /api/v1/articles` |
| `GET /api/articles/highlighted` | `GET /api/v1/articles/highlighted` |
| `GET /api/articles/similar/[id]` | `GET /api/v1/articles/{id}/similar` |
| `GET /api/search/suggestions` | `GET /api/v1/search/suggestions` |
| `GET /api/banners/[position]` | `GET /api/v1/banners/{position}` |
| `POST /api/contact` | `POST /api/v1/contact` |

### Rotas Admin

| Original | Python FastAPI |
|----------|---------------|
| `GET /api/admin/feeds` | `GET /api/v1/admin/feeds` |
| `POST /api/admin/feeds` | `POST /api/v1/admin/feeds` |
| `GET /api/admin/articles` | `GET /api/v1/admin/articles` |
| `POST /api/admin/articles/upload-pdf` | `POST /api/v1/admin/articles/upload-pdf` |
| `POST /api/admin/articles/scrape` | `POST /api/v1/admin/articles/scrape` |
| `GET /api/admin/stats` | `GET /api/v1/admin/stats` |

### Rotas de IA

| Original | Python FastAPI |
|----------|---------------|
| `POST /api/ai/classify` | `POST /api/v1/ai/classify` |
| `POST /api/ai/translate` | `POST /api/v1/ai/translate` |
| `GET /api/ai/status` | `GET /api/v1/ai/status` |

## Configuração de Ambiente

```env
# .env.example
# Database
DATABASE_URL=sqlite+aiosqlite:///./bhub.db

# Security
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Services
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
HUGGINGFACE_API_KEY=

# Image Services
UNSPLASH_ACCESS_KEY=
PEXELS_API_KEY=

# Cron
CRON_SECRET=your-cron-secret

# App
APP_NAME=BHUB
DEBUG=false
ALLOWED_ORIGINS=http://localhost:3000,https://bhub.com.br

# Paths
UPLOAD_DIR=./uploads
LOG_DIR=./logs
```

## Comandos de Execução

```bash
# Desenvolvimento
uvicorn app.main:app --reload --port 8000

# Produção
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Migrações
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Testes
pytest tests/ -v --cov=app
```

## Considerações de Performance

1. **Async/Await**: Todo o código usa async para I/O bound operations
2. **Connection Pooling**: SQLAlchemy com pool de conexões configurado
3. **Background Tasks**: FastAPI BackgroundTasks para operações não-bloqueantes
4. **Caching**: Redis opcional para cache de embeddings e traduções
5. **Rate Limiting**: slowapi para rate limiting nas rotas

## Próximos Passos

1. ✅ Criar estrutura de diretórios
2. ✅ Configurar pyproject.toml e requirements.txt
3. ⬜ Implementar modelos SQLAlchemy
4. ⬜ Implementar schemas Pydantic
5. ⬜ Implementar sistema de autenticação
6. ⬜ Implementar serviços de negócio
7. ⬜ Implementar rotas da API
8. ⬜ Implementar sistema de ML
9. ⬜ Implementar jobs agendados
10. ⬜ Escrever testes
11. ⬜ Documentar API com OpenAPI/Swagger
