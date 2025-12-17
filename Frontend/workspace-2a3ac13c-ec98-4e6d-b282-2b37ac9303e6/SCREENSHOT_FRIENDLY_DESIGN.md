# 📸 Design Share-Friendly - BHub Article View

## Visão Geral

Este documento descreve o design de UI otimizado para screenshots da página de artigo científico do BHub. O objetivo é criar uma interface que funcione naturalmente para compartilhamento em redes sociais (Instagram, LinkedIn, X) sem necessidade de edição adicional.

---

## 🎯 Objetivos do Design

1. **Screenshot-Safe**: Qualquer screenshot deve parecer intencional e profissional
2. **Acadêmico e Neutro**: Manter credibilidade científica
3. **Visualmente Limpo**: Sem ruído visual, hierarquia clara
4. **Multi-Formato**: Funciona para 1:1 (Feed), 9:16 (Stories), 4:5 (Post)

---

## 🧱 Componentes Principais

### 1. ShareableArticleHeader

**Localização**: `src/components/ArticleCard/ShareableArticleHeader.tsx`

**Propósito**: Header contido e screenshot-safe que funciona como card visual standalone.

**Características**:
- Container com background neutro (white/dark)
- Título com hierarquia tipográfica forte
- Badge de categoria e data de publicação
- Source/journal name destacado
- Watermark sutil do BHub (canto inferior direito)
- Margens seguras para cropping

**Uso**:
```tsx
import { ShareableArticleHeader } from '@/components/ArticleCard/ShareableArticleHeader';

<ShareableArticleHeader article={article} />
```

**Modos de Screenshot**:
- **Mode A - Title + Source**: Captura o header completo mostrando título, fonte e categoria
- **Mode B - Title Only**: Foco no título e metadata essencial

---

### 2. AbstractHighlightBlock

**Localização**: `src/components/ArticleCard/AbstractHighlightBlock.tsx`

**Propósito**: Bloco de resumo destacado, visualmente isolado, estilo citação acadêmica.

**Características**:
- Background diferenciado (gray-50/dark)
- Borda lateral esquerda (teal) para destaque
- Quote mark decorativo sutil
- Largura máxima legível
- Label de tradução (se aplicável)
- Referência à fonte no final

**Uso**:
```tsx
import { AbstractHighlightBlock } from '@/components/ArticleCard/AbstractHighlightBlock';

<AbstractHighlightBlock 
  article={article} 
  showTranslationLabel={!!article.abstract_translated}
/>
```

**Modos de Screenshot**:
- **Mode B - Abstract Highlight**: Captura título (menor) + bloco de abstract completo
- **Mode C - Abstract Standalone**: Apenas o bloco de abstract como citação

---

### 3. QuoteHighlight

**Localização**: `src/components/ArticleCard/QuoteHighlight.tsx`

**Propósito**: Componente para destacar frases-chave, otimizado para Stories (9:16).

**Características**:
- Background escuro (navy/gray) com gradiente
- Quote mark grande e decorativo
- Texto em destaque (bold, grande)
- Altura mínima para formato vertical
- Watermark BHub sutil

**Uso**:
```tsx
import { QuoteHighlight } from '@/components/ArticleCard/QuoteHighlight';

<QuoteHighlight 
  text="Frase-chave do artigo aqui..."
  source="Journal Name, 2024"
/>
```

**Modos de Screenshot**:
- **Mode C - Quote/Key Sentence**: Perfeito para Stories, micro-content sharing

---

## 📐 Proporções de Screenshot Suportadas

### Instagram Feed (1:1)
- **Aspect Ratio**: 1:1
- **Recomendado**: Header completo ou Abstract block
- **Classes CSS**: `.screenshot-square`

### Instagram Stories (9:16)
- **Aspect Ratio**: 9:16
- **Recomendado**: QuoteHighlight ou Abstract vertical
- **Classes CSS**: `.screenshot-story`

### Instagram Post (4:5)
- **Aspect Ratio**: 4:5
- **Recomendado**: Header + Abstract combinados
- **Classes CSS**: `.screenshot-portrait`

---

## 🎨 Classes CSS Utilitárias

### `.screenshot-safe`
Adiciona padding seguro para evitar corte de conteúdo importante.

### `.screenshot-card`
Card visual standalone que funciona como imagem completa.

### `.screenshot-text`
Texto otimizado para legibilidade em screenshots (alto contraste).

### `.screenshot-margin`
Margens seguras adaptáveis para diferentes dispositivos.

---

## 🔧 Implementação na ArticleDetailPage

A página de detalhes do artigo (`ArticleDetailPage.tsx`) foi atualizada para usar o novo layout:

1. **Header Principal**: `ShareableArticleHeader` - primeiro elemento visível
2. **Abstract Block**: `AbstractHighlightBlock` - logo abaixo do header
3. **Autores**: Seção discreta, não interfere em screenshots
4. **Ações**: Botões posicionados após conteúdo principal
5. **Conteúdo Secundário**: Tabs e keywords abaixo, não interferem

**Estrutura**:
```
<ShareableArticleHeader />      ← Screenshot Mode A
<AbstractHighlightBlock />        ← Screenshot Mode B
<Authors Section />              ← Discreto
<Action Buttons />                ← Secundário
<Tabs & Content />                ← Secundário
<Keywords />                      ← Secundário
```

---

## 🎯 Modos de Screenshot (Conceituais)

### Mode A – Title + Source
**Para**: Compartilhar descoberta
**Captura**: Título, fonte, categoria, branding BHub
**Componente**: `ShareableArticleHeader`

### Mode B – Abstract Highlight
**Para**: Compartilhamento educacional
**Captura**: Título (menor) + bloco de abstract completo
**Componente**: `AbstractHighlightBlock` ou combinação Header + Abstract

### Mode C – Quote / Key Sentence
**Para**: Micro-content, Stories
**Captura**: Frase destacada com ênfase visual
**Componente**: `QuoteHighlight`

---

## 🎨 Princípios de Design

### 1. Hierarquia Visual Clara
- Títulos grandes e bold
- Subtítulos e metadata menores
- Espaçamento generoso entre elementos

### 2. Background Neutro
- White/dark backgrounds
- Sem gradientes complexos
- Sem efeitos visuais que degradam em screenshots

### 3. Tipografia Acadêmica
- Fontes serif (Roboto Slab) para títulos
- Fontes sans-serif (Raleway) para corpo
- Alto contraste para legibilidade

### 4. Branding Sutil
- Watermark "bhub.online" em canto inferior direito
- Opacidade baixa (10-20%)
- Nunca dominante

### 5. Margens Seguras
- Padding adequado para evitar corte
- Conteúdo centralizado
- Suporte a safe areas (mobile)

---

## 📱 Responsividade

### Mobile (< 640px)
- Padding reduzido
- Fontes menores mas legíveis
- Cards com altura mínima de 350px

### Tablet (641px - 1024px)
- Padding médio
- Fontes balanceadas
- Cards com altura mínima de 450px

### Desktop (> 1025px)
- Padding generoso
- Fontes maiores
- Cards com altura mínima de 500px

---

## ✅ Checklist de Screenshot-Friendliness

Ao criar novos componentes para artigos, verifique:

- [ ] Background neutro (white/dark)
- [ ] Hierarquia tipográfica clara
- [ ] Margens seguras para cropping
- [ ] Conteúdo centralizado
- [ ] Branding sutil (se aplicável)
- [ ] Alto contraste de texto
- [ ] Sem elementos que quebram em crop
- [ ] Funciona em 1:1, 4:5 e 9:16

---

## 🚀 Próximos Passos

1. **Testes de Screenshot**: Capturar screenshots reais em diferentes dispositivos
2. **Otimização de Cores**: Garantir contraste adequado em todos os temas
3. **A/B Testing**: Testar diferentes layouts com usuários
4. **Analytics**: Medir taxa de compartilhamento de screenshots

---

## 📝 Notas Técnicas

- Todos os componentes são client-side (`'use client'`)
- Suporte completo a dark mode
- Acessibilidade: alto contraste, hierarquia semântica
- Performance: componentes leves, sem dependências pesadas

---

**Última atualização**: Dezembro 2024
**Versão**: 1.0.0

