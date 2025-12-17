# BHub Frontend - Repositório de Análise do Comportamento

Frontend moderno do BHub, um repositório científico dedicado à análise do comportamento, construído com Next.js 15, TypeScript e Tailwind CSS.

## 🚀 Stack Tecnológica

- **Framework**: Next.js 15 com App Router
- **Linguagem**: TypeScript 5
- **Styling**: Tailwind CSS 4 com design system customizado
- **UI Components**: shadcn/ui + componentes personalizados
- **State Management**: Zustand
- **Icons**: Lucide React
- **Fonts**: Roboto Slab + Raleway (Google Fonts)
- **Theme**: Dark mode com ThemeProvider
- **Responsividade**: Mobile-first approach

## 🎨 Design System

### Cores BHub
```css
--bhub-dark-gray: #272727
--bhub-light-gray: #F7F7F7
--bhub-teal-primary: #41B5A3
--bhub-teal-light: #B7ECE4
--bhub-navy-dark: #1C3159
--bhub-navy-light: #D6E0EC
--bhub-red-accent: #BA213D
--bhub-red-light: #FAEDED
--bhub-yellow-primary: #FABD4A
--bhub-yellow-light: #FDE6BA
```

### Tipografia
- **Display**: Roboto Slab (títulos)
- **Body**: Raleway (conteúdo)
- **Mono**: Fira Code (código)

## 📁 Estrutura do Projeto

```
src/
├── app/                    # App Router (Next.js 15)
│   ├── page.tsx          # Página inicial
│   ├── articles/         # Listagem de artigos
│   ├── repository/        # Recursos e downloads
│   ├── article/[id]/     # Detalhes do artigo
│   ├── about/            # Sobre o BHub
│   ├── categories/        # Categorias de pesquisa
│   ├── authors/           # Autores em destaque
│   ├── contact/           # Formulário de contato
│   ├── search/            # Busca avançada
│   ├── test/              # Teste de componentes
│   ├── bhub-test/         # Teste de cores BHub
│   ├── simple/            # Teste simples
│   ├── layout.tsx         # Layout principal
│   └── globals.css         # Estilos globais
├── components/             # Componentes UI
│   ├── ArticleCard/        # Cards de artigos
│   ├── Avatar/            # Componentes de avatar
│   ├── Badge/             # Componentes de badge
│   ├── Button/            # Componentes de botão
│   ├── Icon/              # Biblioteca de ícones
│   ├── Layout/            # Layout components
│   ├── Sidebar/           # Sidebar components
│   ├── Theme/             # Theme provider
│   └── ui/                # shadcn/ui components
├── pages/                 # Páginas principais
│   ├── HomePage.tsx        # Página inicial
│   ├── ArticlesPage.tsx    # Listagem de artigos
│   ├── RepositoryPage.tsx  # Repositório de recursos
│   └── ArticleDetailPage.tsx # Detalhes do artigo
├── store/                 # Zustand stores
│   ├── articleStore.ts      # Estado dos artigos
│   ├── themeStore.ts       # Estado do tema
│   └── filterStore.ts      # Estado dos filtros
├── services/              # Serviços de API
│   ├── articleService.ts    # Serviços de artigos
│   ├── categoryService.ts   # Serviços de categorias
│   ├── authorService.ts    # Serviços de autores
│   └── api.ts             # Configurações de API
├── types/                 # Tipos TypeScript
│   ├── article.ts          # Tipos de artigos
│   └── common.ts           # Tipos comuns
├── lib/                   # Utilitários
│   └── utils.ts            # Funções utilitárias
└── hooks/                 # Hooks personalizados
    ├── use-toast.ts         # Hook de toast
    └── use-mobile.ts        # Hook de mobile
```

## 🏗️ Componentes Principais

### ArticleCard
Cards para exibição de artigos com diferentes variantes:
- **ArticleCard**: Card padrão para listagens
- **FeaturedArticleCard**: Card em destaque com gradiente
- **ArticleCardList**: Container com grid responsivo

### Layout Components
- **Header**: Navegação principal com menu mobile
- **Footer**: Rodapé com links organizados
- **MainLayout**: Container principal com tema

### UI Components
- **Badge**: Componente de badge com variantes
- **Avatar**: Avatar circular com iniciais ou imagem
- **Button**: Botões com múltiplas variantes
- **Icon**: Biblioteca de ícones extensível

### Sidebar Components
- **FilterSidebar**: Filtros avançados de busca
- **TrendingSidebar**: Artigos em alta com rankings
- **NewsletterCard**: Formulário de newsletter

## 📱 Páginas Disponíveis

### Página Principal (`/`)
- Layout responsivo com 3 colunas (desktop)
- Artigo em destaque
- Lista de artigos recentes
- Sidebars de filtros e trending

### Listagem de Artigos (`/articles`)
- Paginação infinita
- Filtros por categoria, autor e período
- Ordenação por data, citações ou título
- Layout responsivo

### Repositório (`/repository`)
- Recursos para download
- Guias e templates
- Categorias organizadas
- Métricas de acesso

### Detalhes do Artigo (`/article/[id]`)
- Visualização completa do artigo
- Abas: Resumo, Conteúdo, Referências, Métricas
- Interações: like, bookmark, share
- Informações do autor

### Páginas Institucionais
- **Sobre** (`/about`): Missão, visão e valores
- **Categorias** (`/categories`): Navegação por categorias
- **Autores** (`/authors`): Perfil de pesquisadores
- **Contato** (`/contact`): Formulário de contato

### Funcionalidades
- **Busca** (`/search`): Busca avançada com filtros
- **Testes**: Páginas para validação de componentes

## 🎨 Features Implementadas

### Design System
- ✅ Cores BHub personalizadas
- ✅ Tipografia consistente
- ✅ Dark mode completo
- ✅ Componentes responsivos
- ✅ Gradientes e efeitos

### Funcionalidades
- ✅ Navegação intuitiva
- ✅ Busca avançada
- ✅ Filtros múltiplos
- ✅ Paginação otimizada
- ✅ Interações sociais
- ✅ Newsletter integration
- ✅ Download de recursos

### Acessibilidade
- ✅ Semântica HTML5
- ✅ ARIA labels
- ✅ Navegação por teclado
- ✅ Contraste WCAG AA
- ✅ Focus management

### Performance
- ✅ Code splitting automático
- ✅ Lazy loading de componentes
- ✅ Otimização de imagens
- ✅ Bundle otimizado
- ✅ Build eficiente

## 🚀 Como Usar

### Pré-requisitos
- Node.js 18+
- npm ou yarn

### Instalação
```bash
# Clonar repositório
git clone <repositório>
cd bhub-frontend

# Instalar dependências
npm install

# Iniciar desenvolvimento
npm run dev
```

### Desenvolvimento
```bash
# Servidor de desenvolvimento
npm run dev

# Verificar código
npm run lint

# Build para produção
npm run build
```

### Variáveis de Ambiente
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

## 🔧 Configuração

### Tailwind Config
O projeto usa Tailwind CSS 4 com configuração customizada:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        'bhub-dark-gray': '#272727',
        'bhub-light-gray': '#F7F7F7',
        'bhub-teal-primary': '#41B5A3',
        // ... outras cores BHub
      },
      fontFamily: {
        'display': ['Roboto Slab', 'serif'],
        'body': ['Raleway', 'sans-serif'],
      }
    }
  }
}
```

### TypeScript
Configuração estrita com tipos definidos para:
- Componentes UI
- Estados globais
- Serviços de API
- Estruturas de dados

## 📊 Estado da Aplicação

### Zustand Stores
- **articleStore**: Gerenciamento de artigos e favoritos
- **themeStore**: Estado do tema (dark/light)
- **filterStore**: Filtros ativos e ordenação

### Serviços de API
- **articleService**: CRUD de artigos
- **categoryService**: Gestão de categorias
- **authorService**: Informações de autores
- **api**: Configurações e utilitários HTTP

## 🎯 Deploy

### Produção
```bash
# Build otimizado
npm run build

# Iniciar servidor de produção
npm start
```

### Ambiente
- **Node.js**: 18+
- **Navegadores**: Chrome 90+, Firefox 88+, Safari 14+
- **Responsivo**: Mobile-first design

## 🧪 Testes

### Testes de Componentes
- Página `/test`: Validação de todos os componentes
- Página `/bhub-test`: Teste específico de cores BHub
- Página `/simple`: Teste de funcionalidade básica

### Validação
```bash
# Linting
npm run lint

# Type checking
npm run type-check
```

## 📱 Responsividade

### Breakpoints
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### Layout Adaptativo
- **Desktop**: 3 colunas (sidebar - conteúdo - sidebar)
- **Tablet**: 2 colunas (conteúdo - sidebar)
- **Mobile**: 1 coluna com stack vertical

## 🔄 Integração com Backend

### API Endpoints
- `GET /api/articles`: Listagem de artigos
- `GET /api/articles/:id`: Detalhes do artigo
- `POST /api/favorites/:id`: Gerenciar favoritos
- `GET /api/categories`: Categorias disponíveis
- `GET /api/authors`: Lista de autores

### Comunicação
- Fetch API para requisições HTTP
- Tratamento de erros centralizado
- Loading states e feedback visual
- Cache inteligente de requisições

## 🎨 Contribuição

### Guia de Estilo
- Seguir padrões de código existentes
- Usar componentes já existentes
- Manter consistência visual
- Testar em múltiplos dispositivos

### Fluxo de Trabalho
1. Fork do projeto
2. Branch feature/nome-da-feature
3. Desenvolvimento com commits semânticos
4. Pull request com descrição detalhada
5. Code review e merge

## 📄 Licença

Este projeto está sob licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Contato

- **Issues**: [GitHub Issues](link-do-repositorio/issues)
- **Discussions**: [GitHub Discussions](link-do-repositorio/discussions)
- **Email**: contato@bhub.com.br

---

**Desenvolvido com ❤️ para a comunidade de análise do comportamento**