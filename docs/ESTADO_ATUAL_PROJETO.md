# Estado Atual do Projeto BHUB

**Data da Análise**: Dezembro 2024  
**Versão**: 1.0.0  
**Status**: Em Desenvolvimento Ativo

---

## 📋 Visão Geral

O **BHUB (Behavior Hub)** é uma plataforma web para agregação, análise e classificação automática de artigos científicos na área de **Análise do Comportamento (ABA - Applied Behavior Analysis)**. O projeto foi migrado de Next.js/TypeScript para Python/FastAPI, mantendo todas as funcionalidades originais e adicionando novas capacidades.

### Objetivo Principal

Fornecer uma plataforma centralizada onde pesquisadores, profissionais e estudantes de Análise do Comportamento possam:
- Acessar artigos científicos agregados de múltiplas fontes (RSS, scraping, upload manual)
- Buscar e filtrar artigos por categoria, autor, impacto, etc.
- Visualizar artigos com tradução automática (PT/EN)
- Acompanhar métricas e estatísticas de uso
- Gerenciar conteúdo através de painel administrativo

---

## 🏗️ Arquitetura e Stack Tecnológica

### Backend

| Componente | Tecnologia | Versão |
|------------|-----------|--------|
| **Framework Web** | FastAPI | 0.115+ |
| **Linguagem** | Python | 3.12+ |
| **ORM** | SQLAlchemy | 2.0 (async) |
| **Banco de Dados** | SQLite | com FTS5 (Full-Text Search) |
| **Autenticação** | FastAPI-Users | JWT tokens |
| **Machine Learning** | sentence-transformers | 3.3.0+ |
| **Scheduler** | APScheduler | 3.10.4+ |
| **Logging** | Loguru | 0.7.2+ |

### Frontend

| Componente | Tecnologia | Descrição |
|------------|-----------|-----------|
| **Renderização** | Server-Side Rendering (SSR) | Jinja2 templates |
| **Interatividade** | HTMX | Requisições AJAX sem JavaScript complexo |
| **Estilização** | Tailwind CSS | Framework CSS utility-first |
| **Animações** | Anime.js | Animações suaves e modernas |

### Integrações de IA

- **DeepSeek API**: Classificação e tradução de artigos
- **OpenRouter API**: Fallback para serviços de IA
- **Local LLM** (Opcional): Suporte a modelos locais via llama.cpp (Phi-3-mini)

### Infraestrutura

- **Containerização**: Docker + Docker Compose
- **Deploy**: Suporte a VPS com Nginx + PM2
- **Monitoramento**: Logs estruturados, health checks, analytics

---

## 📁 Estrutura do Projeto

```
Bhub_py/
├── bhub-backend-python/          # Aplicação principal
│   ├── app/
│   │   ├── api/                  # Rotas da API REST
│   │   │   ├── v1/               # API v1
│   │   │   │   ├── admin/        # Endpoints administrativos
│   │   │   │   ├── articles.py   # Artigos
│   │   │   │   ├── categories.py # Categorias
│   │   │   │   ├── search.py     # Busca
│   │   │   │   ├── ai.py         # IA (classificação/tradução)
│   │   │   │   └── ...
│   │   │   └── auth/             # Autenticação
│   │   ├── models/               # Modelos SQLAlchemy (13 modelos)
│   │   ├── schemas/              # Schemas Pydantic (9 schemas)
│   │   ├── services/             # Lógica de negócio (11 serviços)
│   │   ├── ml/                   # Machine Learning
│   │   ├── ai/                   # Integrações de IA
│   │   ├── jobs/                 # Jobs agendados
│   │   ├── core/                 # Utilitários core (16 módulos)
│   │   ├── web/                  # Rotas web (SSR + HTMX)
│   │   ├── static/               # Arquivos estáticos (CSS, JS, imagens)
│   │   ├── templates/            # Templates Jinja2 (27 templates)
│   │   └── main.py               # Aplicação FastAPI
│   ├── alembic/                  # Migrações de banco de dados
│   ├── scripts/                  # Scripts utilitários
│   ├── tests/                    # Testes automatizados
│   └── requirements.txt          # Dependências Python
├── docs/                         # Documentação organizada
│   ├── arquitetura/              # Documentação de arquitetura
│   ├── deploy/                    # Guias de deploy
│   ├── seguranca/                 # Documentação de segurança
│   ├── ui-ux/                     # Documentação UI/UX
│   ├── implementacao/             # Guias de implementação
│   └── configuracao/              # Configurações e setup
└── README.md                      # Documentação principal
```

---

## 🎯 Funcionalidades Principais

### 1. Agregação de Artigos

- **Feeds RSS**: Sincronização automática de 29+ feeds RSS de revistas científicas
- **Web Scraping**: Extração de artigos de sites sem feed RSS
- **Upload de PDF**: Upload manual de artigos em PDF
- **Sincronização Agendada**: Jobs automáticos via APScheduler

### 2. Classificação Automática

- **Machine Learning**: Classificação usando embeddings (sentence-transformers)
- **Modelo**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Categorias**: Clínica, Educação, Organizacional, Pesquisa, Autismo, Notícias, Outros
- **Score de Confiança**: Cada classificação inclui nível de confiança (0-1)

### 3. Tradução Automática

- **Cache de Traduções**: Sistema de cache para evitar retraduções
- **Suporte PT/EN**: Tradução bidirecional de títulos e abstracts
- **Provedores**: DeepSeek API, OpenRouter (fallback), Local LLM (opcional)

### 4. Busca e Filtros

- **Busca Full-Text**: Usando FTS5 do SQLite
- **Filtros Avançados**: Por categoria, autor, data, impacto, idioma
- **Sugestões**: Sistema de autocompletar para buscas
- **Busca Semântica**: Preparado para busca por similaridade (futuro)

### 5. Sistema de Usuários

- **Autenticação JWT**: Tokens de acesso e refresh
- **Roles**: USER e ADMIN
- **Painel Admin**: Interface administrativa completa
- **Sessões**: Rastreamento de sessões de usuários

### 6. Analytics

- **Eventos**: Rastreamento de visualizações, cliques, buscas
- **Sessões**: Análise de comportamento de usuários
- **Métricas**: Agregação de dados para relatórios
- **Respeito a DNT**: Respeita header "Do Not Track"

### 7. Open Graph

- **Geração Automática**: Imagens OG geradas automaticamente
- **Metadados**: Títulos, descrições, imagens otimizadas para redes sociais

### 8. Interface Web (SSR + HTMX)

- **Páginas Principais**:
  - Home com lista de artigos
  - Detalhe do artigo
  - Categorias
  - Busca avançada
  - Contato
  - Login/Admin
- **Responsividade**: Design mobile-first
- **Acessibilidade**: Conformidade com padrões WCAG

---

## 🗄️ Modelos de Dados

### Principais Entidades

| Modelo | Tabela | Descrição |
|--------|--------|-----------|
| `User` | `users` | Usuários do sistema (USER/ADMIN) |
| `Article` | `articles` | Artigos científicos agregados |
| `Category` | `categories` | Categorias de classificação |
| `Feed` | `feeds` | Feeds RSS configurados |
| `Author` | `authors` | Autores dos artigos |
| `PDFMetadata` | `pdf_metadata` | Metadados de PDFs processados |
| `TranslationCache` | `translation_cache` | Cache de traduções |
| `AnalyticsEvent` | `analytics_events` | Eventos de analytics |
| `AnalyticsSession` | `analytics_sessions` | Sessões de usuários |
| `Banner` | `banners` | Banners promocionais |
| `ContactMessage` | `contact_messages` | Mensagens de contato |

### Relacionamentos

- **Article ↔ Category**: Many-to-Many (via `article_categories`)
- **Article ↔ Author**: Many-to-Many (via `article_authors`)
- **Article → Feed**: Many-to-One
- **Article → User**: Many-to-One (uploaded_by)
- **Article → Category**: Many-to-One (primary category)

---

## 🔌 API Endpoints

### Endpoints Públicos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/articles` | Lista artigos (com paginação e filtros) |
| GET | `/api/v1/articles/{id}` | Detalhes de um artigo |
| GET | `/api/v1/articles/highlighted` | Artigos destacados |
| GET | `/api/v1/categories` | Lista categorias |
| GET | `/api/v1/authors` | Lista autores |
| GET | `/api/v1/search` | Busca de artigos |
| GET | `/api/v1/search/suggestions` | Sugestões de busca |
| POST | `/api/v1/contact` | Enviar mensagem de contato |
| GET | `/api/v1/ai/status` | Status dos provedores de IA |

### Endpoints Admin (Requer Autenticação)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/admin/stats` | Estatísticas gerais |
| GET | `/api/v1/admin/analytics` | Dados de analytics |
| POST | `/api/v1/admin/feeds` | Criar feed |
| GET | `/api/v1/admin/feeds` | Listar feeds |
| POST | `/api/v1/admin/feeds/sync-all` | Sincronizar todos os feeds |
| POST | `/api/v1/admin/articles/upload-pdf` | Upload de PDF |
| POST | `/api/v1/admin/articles/scrape` | Scraping de URL |

### Endpoints de IA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ai/classify` | Classificar texto |
| POST | `/api/v1/ai/translate` | Traduzir texto |

---

## 🔐 Segurança

### Implementações de Segurança

- ✅ **Autenticação JWT**: Tokens de acesso (15min) e refresh (7 dias)
- ✅ **Rate Limiting**: Proteção contra abuso (100 req/min)
- ✅ **CSRF Protection**: Tokens CSRF para formulários
- ✅ **Security Headers**: Headers de segurança configurados
- ✅ **Validação de Uploads**: Tipo, tamanho e estrutura de arquivos
- ✅ **Sanitização**: Sanitização de inputs
- ✅ **CORS Configurado**: Origens permitidas explicitamente
- ✅ **Validação de Produção**: Validações automáticas em produção

### Correções de Segurança Aplicadas

- ✅ CVE-2025-55182: Correção de vulnerabilidade crítica
- ✅ Correções de segurança HIGH e CRITICAL
- ✅ Correções de CORS
- ✅ Validação de SECRET_KEY em produção

---

## 📊 Estado de Implementação

### ✅ Funcionalidades Completas

- [x] Sistema de autenticação e autorização
- [x] Agregação de feeds RSS
- [x] Web scraping de artigos
- [x] Upload e processamento de PDFs
- [x] Classificação automática com ML
- [x] Sistema de tradução com cache
- [x] Busca full-text
- [x] Sistema de analytics
- [x] Interface web SSR + HTMX
- [x] Painel administrativo
- [x] Open Graph generation
- [x] Jobs agendados (sincronização)
- [x] Sistema de banners
- [x] Formulário de contato

### 🚧 Em Desenvolvimento

- [ ] Busca semântica (similaridade de embeddings)
- [ ] Melhorias de UI/UX (fase 3)
- [ ] Testes automatizados completos
- [ ] Otimizações de performance
- [ ] Suporte a mais idiomas

### 📝 Planejado

- [ ] Sistema de notificações
- [ ] Exportação de dados
- [ ] API pública documentada
- [ ] Integração com mais fontes
- [ ] Dashboard de analytics avançado

---

## 🛠️ Configuração e Deploy

### Variáveis de Ambiente Principais

```env
# App
APP_NAME=BHUB
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Database
DATABASE_URL=sqlite+aiosqlite:///./bhub.db

# Security
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
ALLOWED_ORIGINS=https://seu-dominio.com

# AI Services
DEEPSEEK_API_KEY=<sua-chave>
OPENROUTER_API_KEY=<sua-chave>

# Scheduler
ENABLE_SCHEDULER=true
SYNC_INTERVAL_HOURS=1
CRON_SECRET=<secret-para-cron-externo>
```

### Opções de Deploy

1. **Docker Compose** (Recomendado)
   - Arquivo: `docker-compose.prod.yml`
   - Inclui Nginx, aplicação, volumes

2. **VPS Manual**
   - Nginx como reverse proxy
   - PM2 para gerenciamento de processo
   - Scripts de deploy disponíveis

3. **Desenvolvimento Local**
   - Uvicorn com reload
   - SQLite local
   - Hot-reload de templates

---

## 📚 Documentação Disponível

A documentação foi organizada nas seguintes categorias:

### Arquitetura
- `MIGRATION_GUIDE.md`: Guia de migração Next.js → Python
- `bhub-stack-recomendada.md`: Stack tecnológica recomendada
- `bhub-design-reference.md`: Referência de design

### Deploy
- `DOCKER_DEPLOY.md`: Deploy com Docker
- `README_DOCKER.md`: Documentação Docker
- `VPS_DEPLOY.md`: Deploy em VPS
- `VPS_MAINTENANCE.md`: Manutenção em VPS
- `VPS_UPLOAD.md`: Upload para VPS

### Segurança
- `SECURITY_AUDIT.md`: Auditoria de segurança
- `SECURITY_REMAINING.md`: Itens de segurança pendentes
- `SECURITY_FIXES_CRITICAL.md`: Correções críticas
- `SECURITY_FIXES_HIGH.md`: Correções de alta prioridade
- `CVE-2025-55182_FIX.md`: Correção de CVE específico
- `CORS_FIX.md`: Correções de CORS

### UI/UX
- `UI_UX_ANALYSIS.md`: Análise de UI/UX
- `UI_UX_SETUP.md`: Setup de UI/UX
- `PLANO_IMPLEMENTACAO_UI_UX.md`: Plano de implementação
- `FASE_1_2_ACESSIBILIDADE.md`: Fase 1.2 - Acessibilidade
- `FASE_2_2_COMPONENTES_FEEDBACK.md`: Fase 2.2 - Componentes
- `FASE_2_3_RESPONSIVIDADE_MOBILE.md`: Fase 2.3 - Mobile
- `FASE_3_APRIMORAMENTOS_UX.md`: Fase 3 - Aprimoramentos
- `PALETA_CORES.md`: Paleta de cores
- `VERIFICAÇÃO_CONTRASTE_CORES.md`: Verificação de contraste

### Implementação
- `IMPLEMENTACAO_TRADUCAO.md`: Sistema de tradução
- `IMPLEMENTAÇÃO_PRIORIDADE_ALTA.md`: Implementações prioritárias
- `CHECKLIST_IMPLEMENTACAO.md`: Checklist de implementação
- `PROGRESSO_IMPLEMENTACAO.md`: Progresso atual
- `PRÓXIMOS_PASSOS.md`: Próximos passos
- `OPEN_GRAPH_IMPLEMENTATION.md`: Open Graph
- `HTMX_FIX_SUMMARY.md`: Correções HTMX

### Configuração
- `DOCUMENTACAO_BACKEND.md`: Documentação completa do backend
- `GUIA_INICIO_RAPIDO.md`: Guia de início rápido
- `FEEDS_RSS.md`: Configuração de feeds RSS
- `ANALYTICS.md`: Sistema de analytics
- `LOCAL_LLM_SETUP.md`: Setup de LLM local

---

## 🧪 Testes

### Estrutura de Testes

- **Framework**: pytest
- **Cobertura**: pytest-cov
- **Localização**: `bhub-backend-python/tests/`
- **Status**: Em desenvolvimento

### Testes Disponíveis

- Testes de artigos (`test_articles.py`)
- Configuração de testes (`conftest.py`)

---

## 📈 Métricas e Monitoramento

### Health Check

- **Endpoint**: `GET /health`
- **Retorna**: Status da aplicação, banco, ML model

### Logs

- **Framework**: Loguru
- **Localização**: `bhub-backend-python/logs/`
- **Rotação**: 10 MB
- **Retenção**: 1 mês
- **Níveis**: INFO, WARNING, ERROR

### Analytics

- **Eventos rastreados**: Visualizações, cliques, buscas
- **Sessões**: Rastreamento de sessões de usuários
- **Métricas agregadas**: Disponíveis via API admin

---

## 🚀 Próximos Passos Recomendados

1. **Completar Testes**: Expandir cobertura de testes automatizados
2. **Otimizações**: Performance de queries, cache, indexação
3. **Busca Semântica**: Implementar busca por similaridade
4. **UI/UX**: Finalizar fase 3 de aprimoramentos
5. **Documentação API**: Documentação pública da API
6. **CI/CD**: Pipeline de integração contínua
7. **Monitoramento**: Alertas e dashboards avançados

---

## 👥 Equipe e Contribuição

Desenvolvido pela equipe BHUB.

### Como Contribuir

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT.

---

## 📞 Contato

Para dúvidas, sugestões ou problemas:
- **Email**: contato@bhub.com.br
- **Issues**: Abra uma issue no repositório

---

**Última Atualização**: Dezembro 2024  
**Versão do Documento**: 1.0.0
