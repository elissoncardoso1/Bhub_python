# BHUB (Behavior Hub) - Documentação de Design

## Visão Geral
BHUB é uma plataforma moderna para agregação e análise de artigos científicos em Análise do Comportamento usando machine learning. O design prioriza usabilidade, responsividade e uma experiência visual profissional.

## Paleta de Cores

### Cores Primárias
- **Azul Principal**: `#2563eb` (blue-600)
- **Azul Escuro**: `#1e40af` (blue-700)
- **Azul Hover**: `#3b82f6` (blue-500)

### Cores de Fundo
- **Background Principal**: `#f8fafc` (slate-50)
- **Background Secundário**: `#ffffff` (white)
- **Background Cards**: `#ffffff` com sombra suave

### Cores de Texto
- **Texto Principal**: `#1e293b` (slate-800)
- **Texto Secundário**: `#64748b` (slate-500)
- **Texto Terciário**: `#94a3b8` (slate-400)

### Cores de Estado
- **Sucesso**: `#10b981` (green-500)
- **Aviso**: `#f59e0b` (amber-500)
- **Erro**: `#ef4444` (red-500)
- **Info**: `#3b82f6` (blue-500)

## Tipografia

### Fonte Principal
- **Família**: Inter (fallback: system-ui, -apple-system, sans-serif)
- **Pesos disponíveis**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

### Hierarquia de Texto
```css
/* Títulos */
h1: 2.25rem (36px) / font-weight: 700 / line-height: 1.2
h2: 1.875rem (30px) / font-weight: 700 / line-height: 1.3
h3: 1.5rem (24px) / font-weight: 600 / line-height: 1.4
h4: 1.25rem (20px) / font-weight: 600 / line-height: 1.4

/* Corpo */
body: 1rem (16px) / font-weight: 400 / line-height: 1.5
small: 0.875rem (14px) / font-weight: 400 / line-height: 1.5
tiny: 0.75rem (12px) / font-weight: 400 / line-height: 1.5
```

## Componentes Principais

### 1. Header / Navbar
```
Características:
- Background: branco (#ffffff)
- Sombra: shadow-sm (0 1px 2px rgba(0, 0, 0, 0.05))
- Altura: 64px
- Padding: px-6 py-4
- Position: fixed top-0, z-index: 50
- Border-bottom: 1px solid #e2e8f0

Elementos:
- Logo BHUB (esquerda)
  - Ícone: 🧠 ou ícone de cérebro
  - Texto: "BHUB" em bold, tamanho 1.5rem
  - Subtítulo: "Behavior Hub" em text-sm, text-slate-500

- Menu de Navegação (centro/direita)
  - Links: text-slate-600, hover:text-blue-600
  - Active state: text-blue-600, border-bottom 2px solid
  - Itens: Início | Artigos | Análises | Sobre

- Ações (direita)
  - Busca rápida (ícone de lupa)
  - Botão de perfil/login
```

### 2. Hero Section (Página Inicial)
```
Características:
- Background: gradient de #f8fafc para #e0f2fe
- Padding: py-20 px-6
- Texto centralizado

Elementos:
- Título principal (h1)
  - "Agregação Inteligente de Artigos em Análise do Comportamento"
  - Color: slate-900
  - Font-weight: 700

- Subtítulo (p)
  - "Powered by Machine Learning"
  - Color: slate-600
  - Font-size: 1.25rem

- CTA Button
  - Background: blue-600
  - Color: white
  - Padding: px-8 py-3
  - Border-radius: rounded-lg (8px)
  - Font-weight: 600
  - Hover: bg-blue-700, transform scale-105
  - Shadow: shadow-lg
```

### 3. Cards de Artigos
```
Estrutura:
.article-card {
  background: white
  border-radius: 12px (rounded-xl)
  padding: 24px (p-6)
  box-shadow: shadow-md
  border: 1px solid #e2e8f0
  transition: all 0.3s ease
  hover: shadow-xl, transform translateY(-2px)
}

Layout interno:
┌─────────────────────────────────────┐
│ 📄 [Badge de Categoria]             │
│                                     │
│ Título do Artigo                    │
│ (font-semibold, text-lg, slate-900) │
│                                     │
│ Autores: Nome, Nome                 │
│ (text-sm, text-slate-600)           │
│                                     │
│ Ano: 2024 | Journal: Nome          │
│ (text-xs, text-slate-500)           │
│                                     │
│ Abstract preview (3 linhas)...      │
│ (text-sm, text-slate-700)           │
│                                     │
│ ┌──────────┐  ┌──────────┐         │
│ │ Ver mais │  │ Download │         │
│ └──────────┘  └──────────┘         │
└─────────────────────────────────────┘

Badges de Categoria:
- ABA: bg-blue-100, text-blue-700
- RFT: bg-purple-100, text-purple-700
- ACT: bg-green-100, text-green-700
- FAP: bg-amber-100, text-amber-700
- DBT: bg-pink-100, text-pink-700
```

### 4. Filtros e Busca
```
Container de Filtros:
- Background: white
- Padding: p-6
- Border-radius: rounded-xl
- Shadow: shadow-md
- Margin-bottom: mb-8

Elementos:
1. Barra de Busca
   - Input com ícone de lupa
   - Placeholder: "Buscar por título, autor, palavras-chave..."
   - Border: 2px solid slate-200
   - Focus: border-blue-500, ring-2 ring-blue-200
   - Border-radius: rounded-lg
   - Padding: px-4 py-2

2. Dropdowns de Filtro
   - Ano de Publicação
   - Categoria/Abordagem
   - Journal
   - Ordenação

   Estilo dos Dropdowns:
   - Border: 1px solid slate-300
   - Background: white
   - Hover: bg-slate-50
   - Focus: border-blue-500
   - Border-radius: rounded-md

3. Botões de Ação
   - "Aplicar Filtros": bg-blue-600, text-white
   - "Limpar": bg-slate-200, text-slate-700
```

### 5. Grid de Resultados
```
Layout:
- Display: grid
- Grid-template-columns: 
  - Mobile: 1 coluna
  - Tablet: 2 colunas (md:grid-cols-2)
  - Desktop: 3 colunas (lg:grid-cols-3)
- Gap: 6 (1.5rem)
- Padding: px-6

Paginação:
- Container: flex, justify-center, items-center
- Margin-top: mt-8
- Buttons: 
  - Números: w-10, h-10, rounded-md
  - Normal: bg-white, text-slate-700
  - Active: bg-blue-600, text-white
  - Hover: bg-slate-100
  - Disabled: opacity-50, cursor-not-allowed
```

### 6. Modal de Detalhes do Artigo
```
Overlay:
- Background: rgba(0, 0, 0, 0.5)
- Position: fixed, inset-0
- Z-index: 100
- Backdrop-blur: blur-sm

Modal:
- Background: white
- Max-width: 4xl (896px)
- Border-radius: rounded-2xl
- Padding: p-8
- Shadow: shadow-2xl
- Max-height: 90vh
- Overflow: auto

Header:
- Título: text-2xl, font-bold, slate-900
- Botão fechar (X): absolute top-4 right-4

Conteúdo:
1. Metadados
   - Autores (com ícone 👤)
   - Data (com ícone 📅)
   - Journal (com ícone 📚)
   - DOI/Link (com ícone 🔗)

2. Abstract
   - Section title: text-lg, font-semibold
   - Texto: text-slate-700, leading-relaxed

3. Keywords
   - Tags: inline-block, bg-slate-100
   - Text: text-slate-600, text-sm
   - Padding: px-3 py-1
   - Border-radius: rounded-full
   - Margin: mr-2 mb-2

4. Ações
   - Download PDF: bg-blue-600, text-white
   - Salvar/Favoritar: bg-slate-200, text-slate-700
   - Compartilhar: bg-slate-200, text-slate-700
```

### 7. Dashboard de Análises
```
Layout de Cards Estatísticos:
- Grid: 4 colunas (responsive)
- Gap: 6

Card Estatístico:
┌─────────────────────┐
│ 📊 Ícone            │
│                     │
│ 1,234               │
│ (text-3xl, bold)    │
│                     │
│ Total de Artigos    │
│ (text-sm, muted)    │
└─────────────────────┘

Cores dos Cards:
- Artigos: bg-blue-50, border-blue-200, text-blue-600
- Análises: bg-purple-50, border-purple-200, text-purple-600
- Citações: bg-green-50, border-green-200, text-green-600
- Autores: bg-amber-50, border-amber-200, text-amber-600

Gráficos:
- Container: bg-white, rounded-xl, shadow-md, p-6
- Título do gráfico: text-lg, font-semibold, mb-4
- Usar Chart.js ou similar para visualizações
```

### 8. Footer
```
Características:
- Background: slate-900
- Color: slate-300
- Padding: py-12 px-6
- Margin-top: mt-20

Layout:
- Grid: 4 colunas (responsive)
- Gap: 8

Seções:
1. Sobre o BHUB
   - Logo e descrição breve
   - Color: slate-400

2. Links Rápidos
   - Lista de navegação
   - Hover: text-white

3. Recursos
   - API
   - Documentação
   - Suporte

4. Contato
   - Email
   - Redes sociais (ícones)

Copyright:
- Border-top: 1px solid slate-800
- Padding-top: pt-8
- Text-align: center
- Text-size: text-sm
- Color: slate-500
```

## Animações e Transições

### Transições Padrão
```css
transition: all 0.3s ease
```

### Hover Effects
```css
/* Cards */
hover: transform translateY(-2px), shadow-xl

/* Botões */
hover: transform scale(105%), brightness(110%)

/* Links */
hover: color transition (0.2s ease)
```

### Loading States
```css
/* Skeleton Loader */
- Background: linear-gradient shimmer
- Animation: pulse 2s infinite
- Border-radius: match do elemento

/* Spinner */
- Border: 3px solid slate-200
- Border-top: 3px solid blue-600
- Animation: spin 1s linear infinite
```

## Responsividade

### Breakpoints
```css
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
2xl: 1536px /* Extra large */
```

### Padrões Mobile-First
```css
/* Mobile (default) */
- Padding: px-4
- Font-size: base
- Grid: 1 coluna

/* Tablet (md:) */
- Padding: px-6
- Grid: 2 colunas

/* Desktop (lg:) */
- Padding: px-8
- Grid: 3 colunas
- Sidebar visível
```

## Acessibilidade

### Contraste
- Todos os textos atendem WCAG AA (4.5:1 mínimo)
- Botões importantes: contraste AAA (7:1)

### Focus States
```css
focus: outline-2, outline-offset-2, outline-blue-600
focus-visible: ring-2, ring-blue-500, ring-offset-2
```

### ARIA Labels
- Todos os botões de ícone têm aria-label
- Modals têm aria-modal="true"
- Navegação tem role="navigation"

## Estados de Componentes

### Empty State
```
- Ícone grande centralizado (📭)
- Texto: "Nenhum artigo encontrado"
- Subtexto: "Tente ajustar os filtros"
- Botão: "Limpar filtros"
```

### Error State
```
- Ícone: ⚠️ ou ❌
- Background: red-50
- Border: red-200
- Text: red-700
- Botão de retry: red-600
```

### Success State
```
- Ícone: ✓
- Background: green-50
- Border: green-200
- Text: green-700
- Auto-dismiss após 3s
```

## Ícones

### Biblioteca Recomendada
- Lucide Icons ou Heroicons
- Tamanho padrão: 20px (w-5 h-5)
- Tamanho grande: 24px (w-6 h-6)
- Color: inherit do parent

### Ícones Principais
```
🔍 Busca
📄 Documento/Artigo
📚 Journal/Biblioteca
👤 Autor/Perfil
📅 Data/Calendário
🔗 Link/URL
⬇️ Download
❤️ Favorito
📊 Estatísticas/Gráficos
⚙️ Configurações
🔔 Notificações
✖️ Fechar/Cancelar
✓ Confirmar/Sucesso
⚠️ Aviso/Alerta
```

## Estrutura de Layout HTMX

### Template Base
```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BHUB - Behavior Hub</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body class="bg-slate-50 font-sans">
    <!-- Header -->
    <header>...</header>
    
    <!-- Main Content -->
    <main hx-boost="true">
        <!-- Content dinâmico aqui -->
    </main>
    
    <!-- Footer -->
    <footer>...</footer>
</body>
</html>
```

### Padrões HTMX
```html
<!-- Busca com debounce -->
<input 
    type="search" 
    name="q"
    hx-get="/search"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#results"
    hx-indicator="#spinner"
>

<!-- Paginação -->
<button 
    hx-get="/articles?page=2"
    hx-target="#article-list"
    hx-swap="outerHTML"
>
    Próxima Página
</button>

<!-- Modal -->
<button 
    hx-get="/article/123"
    hx-target="#modal"
    hx-swap="innerHTML"
>
    Ver Detalhes
</button>

<!-- Filtros -->
<form 
    hx-get="/filter"
    hx-target="#results"
    hx-trigger="change"
>
    <!-- Filtros aqui -->
</form>
```

## Notas para Implementação HTMX

1. **Usar hx-boost** para navegação SPA-like
2. **Loading indicators** com hx-indicator
3. **Swap strategies**: innerHTML para conteúdo, outerHTML para substituição completa
4. **Debounce em buscas**: delay:500ms
5. **Preservar estado de scroll** com hx-preserve
6. **Transições suaves** com View Transitions API ou CSS transitions
7. **Error handling** com hx-on::after-request
8. **Progressive enhancement**: funcional sem JavaScript

## Checklist de Migração

- [ ] Estrutura HTML semântica replicada
- [ ] Todas as classes Tailwind CSS aplicadas
- [ ] Paleta de cores consistente
- [ ] Tipografia correta (Inter font)
- [ ] Componentes responsivos (mobile-first)
- [ ] Animações e transições funcionando
- [ ] Estados de loading implementados
- [ ] Modals com HTMX
- [ ] Busca com debounce
- [ ] Paginação dinâmica
- [ ] Filtros reativos
- [ ] Acessibilidade (ARIA, focus states)
- [ ] Error handling
- [ ] Empty states
- [ ] Footer completo

---

**Última atualização**: Dezembro 2024
**Versão**: 2.0 (Migração HTMX)
