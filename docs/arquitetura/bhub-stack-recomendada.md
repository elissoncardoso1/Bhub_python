# Stack Recomendada para BHUB - HTMX + Python

> STATUS: HISTÓRICO
> Este documento não representa necessariamente a arquitetura atual.
> Consulte docs/architecture/CURRENT_ARCHITECTURE.md.
>
> Recomendação escrita para a fase de migração Next.js → Python (FastAPI 0.109+, Tailwind por
> CDN, Prisma Python como opção de ORM). A stack efetivamente adotada é a descrita em
> `docs/architecture/CURRENT_ARCHITECTURE.md` § 1 (Tailwind é compilado localmente para
> `app/static/css/output.css`; o ORM é SQLAlchemy 2.0 async).

## Backend Python

### Framework Web: FastAPI
**Recomendação: FastAPI 0.109+**

```bash
pip install fastapi uvicorn[standard] python-multipart jinja2
```

**Por que FastAPI?**
- ✅ Excelente integração com HTMX
- ✅ Performance superior (baseado em Starlette/ASGI)
- ✅ Suporte nativo a async/await
- ✅ Validação automática com Pydantic
- ✅ Documentação automática (OpenAPI)
- ✅ Fácil renderização de templates HTML

**Alternativa:** Flask com extensões
```bash
pip install flask flask-htmx
```

### Template Engine: Jinja2
**Versão: Jinja2 3.1+**

```bash
pip install jinja2
```

**Por que Jinja2?**
- ✅ Integração perfeita com FastAPI e Flask
- ✅ Herança de templates
- ✅ Macros reutilizáveis (ideal para componentes HTMX)
- ✅ Filtros personalizados
- ✅ Performance excelente

### Banco de Dados

**ORM: SQLAlchemy 2.0+ ou Prisma Python**
```bash
pip install sqlalchemy asyncpg  # PostgreSQL async
pip install alembic  # Migrations
```

**Alternativa NoSQL:**
```bash
pip install motor  # MongoDB async
pip install beanie  # ODM para MongoDB
```

### Validação: Pydantic
```bash
pip install pydantic pydantic-settings
```

### Bibliotecas Essenciais
```bash
pip install python-dotenv  # Variáveis de ambiente
pip install httpx  # Cliente HTTP async
pip install python-jose[cryptography]  # JWT
pip install passlib[bcrypt]  # Hashing de senhas
pip install python-multipart  # Upload de arquivos
```

## Frontend

### HTMX
**Versão: 1.9.10+ (2.0 quando estável)**

```html
<!-- Via CDN (desenvolvimento) -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Extensões úteis -->
<script src="https://unpkg.com/htmx.org/dist/ext/response-targets.js"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/loading-states.js"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/debug.js"></script>
```

**Extensões Recomendadas:**
- `response-targets` - Diferentes targets por código HTTP
- `loading-states` - Estados de loading automáticos
- `preload` - Preload de conteúdo
- `head-support` - Atualização de head/meta tags
- `multi-swap` - Múltiplos swaps em uma requisição

### CSS Framework: Tailwind CSS
**Versão: 3.4+**

```html
<!-- Via CDN (desenvolvimento apenas) -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Produção: CLI -->
```

```bash
npm install -D tailwindcss
npx tailwindcss init
```

**tailwind.config.js:**
```javascript
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    }
  },
  plugins: []
}
```

**Alternativa:** DaisyUI (componentes prontos sobre Tailwind)
```bash
npm install -D daisyui@latest
```

### Ícones SVG: Lucide Icons
**Recomendação: Lucide (fork moderno do Feather Icons)**

**Opção 1: Via CDN**
```html
<script src="https://unpkg.com/lucide@latest"></script>
<script>
  lucide.createIcons();
</script>

<!-- Uso -->
<i data-lucide="search"></i>
<i data-lucide="download" class="w-5 h-5 text-blue-600"></i>
```

**Opção 2: Sprite SVG (Recomendado para produção)**
```python
# Download do sprite SVG
# https://unpkg.com/lucide-static@latest/sprite.svg
```

```html
<!-- No base template -->
<svg style="display: none;">
  <use href="/static/icons/lucide-sprite.svg"></use>
</svg>

<!-- Uso -->
<svg class="w-5 h-5">
  <use href="#lucide-search"></use>
</svg>
```

**Opção 3: Helper Python para ícones inline**
```python
# utils/icons.py
from pathlib import Path

class LucideIcons:
    def __init__(self, icons_dir: str = "static/icons/lucide"):
        self.icons_dir = Path(icons_dir)
    
    def get(self, name: str, css_class: str = "w-5 h-5") -> str:
        icon_path = self.icons_dir / f"{name}.svg"
        if icon_path.exists():
            svg_content = icon_path.read_text()
            # Adicionar classes CSS
            svg_content = svg_content.replace('<svg', f'<svg class="{css_class}"')
            return svg_content
        return ""

# No Jinja2
from jinja2 import Environment
icons = LucideIcons()
env.globals['icon'] = icons.get
```

```html
<!-- Uso no template -->
{{ icon('search', 'w-6 h-6 text-blue-600') | safe }}
```

**Alternativas de Ícones SVG:**

1. **Heroicons** (Tailwind UI)
   - https://heroicons.com/
   - Outline e Solid variants
   - Perfeito para Tailwind

2. **Tabler Icons**
   - https://tabler-icons.io/
   - Mais de 4000 ícones
   - Consistente e moderno

3. **Phosphor Icons**
   - https://phosphoricons.com/
   - 6 estilos diferentes
   - Muito flexível

### Alpine.js (Opcional, mas útil)
**Para interatividade leve no cliente**

```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

**Casos de uso:**
- Dropdowns
- Modals simples
- Tabs
- Tooltips
- Validação de formulário no cliente

**Exemplo:**
```html
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open" x-transition>
    Conteúdo
  </div>
</div>
```

### Hyperscript (Alternativa ao Alpine.js)
**Sintaxe mais legível para comportamentos simples**

```html
<script src="https://unpkg.com/hyperscript.org@0.9.12"></script>

<button _="on click toggle .hidden on #menu">
  Menu
</button>
```

## Estrutura de Projeto Recomendada

```
bhub/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configurações
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── article.py
│   │   └── user.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── article.py
│   │   └── user.py
│   ├── routes/                 # Rotas/Endpoints
│   │   ├── __init__.py
│   │   ├── articles.py
│   │   ├── search.py
│   │   └── auth.py
│   ├── services/               # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── article_service.py
│   │   └── ml_service.py
│   └── utils/                  # Utilitários
│       ├── __init__.py
│       ├── icons.py
│       └── helpers.py
├── templates/
│   ├── base.html               # Template base
│   ├── components/             # Componentes reutilizáveis
│   │   ├── navbar.html
│   │   ├── card.html
│   │   ├── modal.html
│   │   └── pagination.html
│   ├── pages/                  # Páginas completas
│   │   ├── home.html
│   │   ├── articles.html
│   │   └── article_detail.html
│   └── partials/               # Fragmentos HTMX
│       ├── article_list.html
│       ├── search_results.html
│       └── filters.html
├── static/
│   ├── css/
│   │   ├── input.css          # Tailwind source
│   │   └── output.css         # Tailwind compiled
│   ├── js/
│   │   ├── main.js
│   │   └── htmx-config.js
│   ├── icons/
│   │   ├── lucide/            # Ícones individuais
│   │   └── sprite.svg         # Sprite completo
│   └── images/
├── tests/
│   ├── __init__.py
│   ├── test_articles.py
│   └── test_search.py
├── alembic/                    # Migrations
│   └── versions/
├── requirements.txt
├── pyproject.toml
├── .env
├── .env.example
├── tailwind.config.js
├── package.json
└── README.md
```

## Exemplo de Implementação

### 1. Setup FastAPI com Jinja2

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="BHUB")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Adicionar helpers customizados
from app.utils.icons import LucideIcons
icons = LucideIcons()
templates.env.globals['icon'] = icons.get

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "pages/home.html",
        {"request": request}
    )
```

### 2. Template Base com HTMX

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}BHUB - Behavior Hub{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link href="/static/css/output.css" rel="stylesheet">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    
    <!-- Alpine.js (opcional) -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    {% block extra_head %}{% endblock %}
</head>
<body class="bg-slate-50 font-sans antialiased">
    <!-- Navbar -->
    {% include 'components/navbar.html' %}
    
    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    {% include 'components/footer.html' %}
    
    <!-- Modals Container -->
    <div id="modal-container"></div>
    
    <!-- Toast/Notifications -->
    <div id="toast-container" class="fixed top-4 right-4 z-50"></div>
    
    <script>
        // Inicializar ícones Lucide
        lucide.createIcons();
        
        // Reinicializar após swaps HTMX
        document.body.addEventListener('htmx:afterSwap', () => {
            lucide.createIcons();
        });
    </script>
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### 3. Componente HTMX (Card de Artigo)

```html
<!-- templates/components/card.html -->
<div class="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 p-6 border border-slate-200">
    <!-- Badge de Categoria -->
    <span class="inline-block px-3 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-700 mb-3">
        {{ article.category }}
    </span>
    
    <!-- Título -->
    <h3 class="text-lg font-semibold text-slate-900 mb-2">
        {{ article.title }}
    </h3>
    
    <!-- Autores -->
    <div class="flex items-center gap-2 text-sm text-slate-600 mb-2">
        {{ icon('user', 'w-4 h-4 inline') | safe }}
        <span>{{ article.authors | join(', ') }}</span>
    </div>
    
    <!-- Metadados -->
    <div class="flex items-center gap-4 text-xs text-slate-500 mb-3">
        <span class="flex items-center gap-1">
            {{ icon('calendar', 'w-3 h-3') | safe }}
            {{ article.year }}
        </span>
        <span class="flex items-center gap-1">
            {{ icon('book', 'w-3 h-3') | safe }}
            {{ article.journal }}
        </span>
    </div>
    
    <!-- Abstract Preview -->
    <p class="text-sm text-slate-700 line-clamp-3 mb-4">
        {{ article.abstract }}
    </p>
    
    <!-- Ações -->
    <div class="flex gap-2">
        <button 
            class="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            hx-get="/article/{{ article.id }}"
            hx-target="#modal-container"
            hx-swap="innerHTML"
        >
            {{ icon('eye', 'w-4 h-4') | safe }}
            Ver mais
        </button>
        
        <button 
            class="px-4 py-2 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 transition"
            hx-get="/download/{{ article.id }}"
            hx-trigger="click"
        >
            {{ icon('download', 'w-4 h-4') | safe }}
        </button>
    </div>
</div>
```

### 4. Rota HTMX para Busca

```python
# app/routes/search.py
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/search")
async def search_articles(
    request: Request,
    q: str = Query(default=""),
    category: str = Query(default=None),
    page: int = Query(default=1)
):
    # Lógica de busca
    articles = await search_service.search(
        query=q,
        category=category,
        page=page
    )
    
    # Retorna apenas o fragmento HTML (partial)
    return templates.TemplateResponse(
        "partials/article_list.html",
        {
            "request": request,
            "articles": articles,
            "page": page
        }
    )
```

### 5. Helper para Ícones

```python
# app/utils/icons.py
from pathlib import Path
from functools import lru_cache

class LucideIcons:
    def __init__(self, icons_dir: str = "static/icons/lucide"):
        self.icons_dir = Path(icons_dir)
    
    @lru_cache(maxsize=128)
    def get(self, name: str, css_class: str = "w-5 h-5") -> str:
        """
        Retorna o SVG do ícone com classes CSS aplicadas
        
        Args:
            name: Nome do ícone (ex: 'search', 'download')
            css_class: Classes CSS do Tailwind
        
        Returns:
            String com o SVG completo
        """
        icon_path = self.icons_dir / f"{name}.svg"
        
        if not icon_path.exists():
            return f'<!-- Ícone {name} não encontrado -->'
        
        svg_content = icon_path.read_text()
        
        # Adicionar classes CSS
        if 'class="' in svg_content:
            svg_content = svg_content.replace(
                'class="',
                f'class="{css_class} '
            )
        else:
            svg_content = svg_content.replace(
                '<svg',
                f'<svg class="{css_class}"'
            )
        
        return svg_content
```

## Requirements.txt

```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0

# Templates
jinja2==3.1.3

# Database
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Utils
python-dotenv==1.0.0
httpx==0.26.0

# Development
pytest==7.4.3
pytest-asyncio==0.23.3
black==23.12.1
ruff==0.1.11
```

## Package.json (para Tailwind)

```json
{
  "name": "bhub",
  "version": "1.0.0",
  "scripts": {
    "dev": "tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch",
    "build": "tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0"
  }
}
```

## Bibliotecas Adicionais Úteis

### Para ML/Análise
```bash
pip install scikit-learn pandas numpy
pip install sentence-transformers  # Embeddings
pip install spacy  # NLP
```

### Para PDFs
```bash
pip install pypdf2 pdfplumber
```

### Para Scraping
```bash
pip install beautifulsoup4 httpx
```

### Para Cache
```bash
pip install redis hiredis
pip install aiocache
```

### Para Background Jobs
```bash
pip install celery  # Com Redis
# ou
pip install arq  # Async, mais leve
```

## Vantagens desta Stack

### HTMX
✅ Menos JavaScript
✅ Server-side rendering
✅ SEO-friendly
✅ Progressive enhancement
✅ Menor complexidade

### FastAPI
✅ Performance excelente
✅ Async nativo
✅ Type hints
✅ Validação automática
✅ Documentação automática

### Tailwind CSS
✅ Utility-first
✅ Customizável
✅ Bundle pequeno (com purge)
✅ Design consistente
✅ Desenvolvimento rápido

### Lucide Icons
✅ SVG otimizado
✅ Consistente
✅ Customizável
✅ Open source
✅ Tree-shakeable

## Comandos de Setup

```bash
# 1. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Instalar Node/Tailwind
npm install

# 4. Download de ícones Lucide
mkdir -p static/icons/lucide
# Baixar de: https://github.com/lucide-icons/lucide/tree/main/icons

# 5. Compilar Tailwind
npm run dev

# 6. Rodar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Recursos e Documentação

- **HTMX**: https://htmx.org/docs/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Lucide Icons**: https://lucide.dev/
- **Jinja2**: https://jinja.palletsprojects.com/
- **Alpine.js**: https://alpinejs.dev/

---

**Pronto para começar!** 🚀
