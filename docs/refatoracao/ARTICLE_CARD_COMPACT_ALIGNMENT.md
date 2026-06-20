# Alinhamento do Article Card Compacto com Página de Detalhe

**Data:** 2026-01-26  
**Status:** ✅ Implementado

---

## 📋 Resumo

Alinhamento 100% do Article Card COMPACTO com a página de detalhe do artigo. O card compacto agora funciona como uma "prévia" direta da página, mantendo mesma ordem de informação, mesmos rótulos e mesmas ações.

**Fonte de verdade:** Página de detalhe do artigo (`article_detail_content.html`)

---

## 🎯 Objetivos Alcançados

1. ✅ **Chip único**: Removido "PERIÓDICO", mantido apenas categoria (ex: "PESQUISA")
2. ✅ **Título**: line-clamp 1 (mobile), 2 (desktop)
3. ✅ **Autores**: Formato "Autor principal et al." em linha separada
4. ✅ **Metadados**: Ordem alinhada (Data • Journal • Idioma • Impacto • DOI)
5. ✅ **DOI**: Link discreto "DOI 10.xxxx/xxxxx"
6. ✅ **Ações no topo**: Salvar, Copiar DOI, Compartilhar (ícones compactos)
7. ✅ **Ações no rodapé**: "Ler original", "Ver detalhes" (CTAs compactos)
8. ✅ **Estado ativo**: `.is-active` com realce discreto (ring/borda + fundo)

---

## 📁 Arquivos Modificados

### 1. `/bhub-backend-python/app/templates/components/card.html`

#### Mudanças Principais:

**Antes:**
- Chip duplicado: categoria + "PERIÓDICO"
- Metadados: Autor • Journal • Data (ordem diferente)
- Ações no topo: apenas Salvar
- Sem DOI visível
- Autores misturados com metadados

**Depois:**
- **Chip único**: Apenas categoria (ex: "PESQUISA")
- **Autores separados**: Linha própria com ícone
- **Metadados reordenados**: Data • Journal • Idioma • Impacto • DOI
- **Ações no topo**: Salvar, Copiar DOI, Compartilhar
- **DOI**: Link discreto na metadata bar

---

### 2. `/bhub-backend-python/app/static/css/article-card.css`

#### Novos Estilos:

```css
/* Autores (formato curto) */
.article-authors
.authors-short

/* Novos elementos de metadata */
.metadata-language
.metadata-impact-inline (com classes .high, .medium, .low)
.metadata-doi

/* Versão compacta ajustada */
.article-card--compact .article-authors
.article-card--compact .metadata-language
.article-card--compact .metadata-impact-inline
.article-card--compact .metadata-doi
```

#### Ajustes na Versão Compacta:

- **Título**: line-clamp 1 (mobile), 2 (desktop) ✓
- **Autores**: Estilo compacto com ícone menor
- **Metadados**: Ordem alinhada, flex-wrap para quebra limpa
- **DOI**: Truncado com ellipsis (max-width: 100px)

---

### 3. `/bhub-backend-python/app/static/js/app.js`

#### Novas Funções Globais:

```javascript
window.copyDOI(doi)        // Copia URL do DOI
window.shareArticle(id, title)  // Compartilha via Web Share API ou copia URL
window.toggleSaveArticle(id)    // Placeholder para funcionalidade futura
```

---

## 🔄 Diferenças por Seção

### 1. Chip (Badge)

**Antes:**
```html
<span class="article-tag category-pesquisa">PESQUISA</span>
<span class="article-tag type-periodico">PERIÓDICO</span>
```

**Depois:**
```html
<span class="article-tag category-pesquisa">PESQUISA</span>
<!-- PERIÓDICO removido -->
```

**Justificativa:** Página de detalhe mostra apenas categoria. Chip "PERIÓDICO" era redundante e competia visualmente com a categoria.

---

### 2. Título

**Antes:**
```css
-webkit-line-clamp: 2; /* Sempre 2 linhas */
```

**Depois:**
```css
/* Mobile */
-webkit-line-clamp: 1;

/* Desktop (≥640px) */
-webkit-line-clamp: 2;
```

**Justificativa:** Versão compacta deve ser mais densa no mobile, mas permitir 2 linhas em telas maiores.

---

### 3. Autores

**Antes:**
```html
<!-- Misturado com metadados -->
<span class="metadata-author">Autor • Journal • Data</span>
```

**Depois:**
```html
<!-- Linha separada -->
<div class="article-authors">
    <div class="authors-short">
        {{ icon('users') }}
        <span>Autor principal et al.</span>
    </div>
</div>
```

**Justificativa:** Alinhado com página de detalhe, onde autores têm linha própria com ícone.

---

### 4. Metadados

**Antes:**
```
Autor • Journal • Data
```

**Depois:**
```
Data • Journal • Idioma • Impacto • DOI
```

**Justificativa:** Mesma ordem da página de detalhe. Facilita reconhecimento visual ao abrir a página.

---

### 5. DOI

**Antes:**
- Não visível no card

**Depois:**
```html
<a href="https://doi.org/{{ article.doi }}" class="metadata-doi">
    DOI {{ article.doi }}
</a>
```

**Justificativa:** Página de detalhe mostra DOI. Card deve ter acesso rápido ao DOI.

---

### 6. Ações no Topo

**Antes:**
```html
<button>Salvar</button>
<a href="...">Abrir</a>
```

**Depois:**
```html
<button aria-label="Salvar">Salvar</button>
<button aria-label="Copiar DOI">Copiar DOI</button>
<button aria-label="Compartilhar">Compartilhar</button>
```

**Justificativa:** Alinhado com action bar da página de detalhe. Mesmas ações, mesmos ícones.

---

### 7. Ações no Rodapé

**Antes:**
```html
<a>Ler original</a>
<a>Ver detalhes</a>
```

**Depois:**
```html
<a>Ler original</a>  <!-- Texto fixo, não condicional -->
<a>Ver detalhes</a>  <!-- Texto fixo, não condicional -->
```

**Justificativa:** Textos consistentes com página de detalhe ("Ler artigo original" → "Ler original" no compacto).

---

## 🎨 Estados e Interações

### Estado Ativo (`.is-active`)

**Implementação:**
- Classe aplicada via `keyboard-shortcuts.js` (j/k navigation)
- Realce discreto: ring 2px + sombra + background hover
- Não altera layout (apenas visual)

**CSS:**
```css
.article-card--compact.is-active {
    box-shadow: 0 0 0 2px var(--color-primary-400), var(--shadow-sm);
    background: var(--color-bg-hover);
}
```

---

### Focus Visible

**Todos os elementos interativos:**
- Botões de ação: `outline: 2px solid var(--color-primary-400)`
- Links: `outline: 2px solid var(--color-primary-400)`
- DOI link: `outline: 2px solid var(--color-primary-400)`

---

## 📱 Responsividade

### Mobile (< 640px)
- Título: 1 linha
- Metadados: quebra com flex-wrap
- DOI: truncado (max-width: 100px)
- Botões do rodapé: apenas ícones (texto oculto via sr-only)

### Desktop (≥ 640px)
- Título: 2 linhas
- Metadados: linha única quando possível
- DOI: visível completo
- Botões do rodapé: ícone + texto

---

## ♿ Acessibilidade

### Implementado:
- ✅ `aria-label` em todos os botões de ação
- ✅ `sr-only` para labels acessíveis
- ✅ `role="list"` e `role="listitem"` na metadata bar
- ✅ `role="group"` nas action bars
- ✅ Focus visível em todos os elementos interativos
- ✅ `min-height: 44px` em botões (WCAG touch target)
- ✅ Suporte a `prefers-reduced-motion`

### Navegação por Teclado:
- ✅ Tab order lógico
- ✅ j/k navigation via `keyboard-shortcuts.js`
- ✅ `.is-active` aplicado corretamente
- ✅ Enter/Space ativam botões

---

## 🧪 Checklist de Testes

### Lista com 20+ Itens (Densidade e Scan)

- [ ] **Chip único visível**: Apenas categoria, sem "PERIÓDICO"
- [ ] **Título legível**: 1 linha mobile, 2 desktop
- [ ] **Autores formatados**: "Autor principal et al." com ícone
- [ ] **Metadados ordenados**: Data • Journal • Idioma • Impacto • DOI
- [ ] **DOI clicável**: Link abre em nova aba
- [ ] **Ações no topo**: Salvar, Copiar DOI, Compartilhar (ícones)
- [ ] **Ações no rodapé**: "Ler original", "Ver detalhes" (CTAs)
- [ ] **Espaçamento adequado**: Não muito denso, não muito espaçado
- [ ] **Hierarquia visual**: Título > Autores > Metadados > Ações
- [ ] **Cores consistentes**: Impacto (high/medium/low) alinhado com página
- [ ] **Ícones consistentes**: Mesmos ícones da página de detalhe
- [ ] **Texto truncado**: Journal e DOI com ellipsis quando necessário
- [ ] **Separadores visíveis**: "•" entre metadados
- [ ] **Estado hover**: Todos os elementos interativos respondem
- [ ] **Estado active**: Botões mostram feedback ao clicar
- [ ] **Estado focus**: Outline visível em navegação por teclado
- [ ] **Estado is-active**: Realce discreto em navegação j/k
- [ ] **Coerência visual**: Ao abrir página, usuário reconhece mesma ordem
- [ ] **Rótulos idênticos**: Mesmos textos da página de detalhe
- [ ] **Ações funcionais**: Copiar DOI, Compartilhar funcionam

### Mobile (Quebra e Touch Targets)

- [ ] **Quebra limpa**: Metadados quebram sem sobreposição
- [ ] **Touch targets**: Botões ≥ 44x44px
- [ ] **Ícones clicáveis**: Área de toque adequada
- [ ] **DOI truncado**: Não quebra layout
- [ ] **Botões do rodapé**: Apenas ícones (texto oculto)
- [ ] **Scroll horizontal**: Não necessário
- [ ] **Padding adequado**: Conteúdo não cola nas bordas

### Teclado (Tab + j/k, Foco Visível)

- [ ] **Tab navigation**: Navega por todos os elementos interativos
- [ ] **j/k navigation**: Move entre cards, aplica `.is-active`
- [ ] **Focus visível**: Outline aparece apenas com teclado
- [ ] **Enter/Space**: Ativa botões corretamente
- [ ] **Escape**: Remove `.is-active` (se aplicável)
- [ ] **Ordem de tab**: Lógica (chip → título → ações → rodapé)
- [ ] **Focus trap**: Não fica preso em nenhum elemento

### Ações (Salvar/Copiar/Compartilhar)

- [ ] **Salvar**: Feedback visual (placeholder implementado)
- [ ] **Copiar DOI**: Copia URL completa (https://doi.org/...)
- [ ] **Compartilhar**: Web Share API ou fallback (copia URL)
- [ ] **Feedback**: Toast/console log após ações
- [ ] **Erros**: Tratamento de erros (clipboard não disponível, etc.)
- [ ] **Acessibilidade**: Ações anunciadas por screen readers

### Coerência Visual

- [ ] **Ao abrir página**: Mesma ordem de informação reconhecível
- [ ] **Mesmos rótulos**: "Ler original", "Ver detalhes", etc.
- [ ] **Mesmos ícones**: bookmark, copy, share-2, external-link, eye
- [ ] **Mesmas cores**: Impacto (high/medium/low) idênticas
- [ ] **Mesma tipografia**: Tamanhos e pesos consistentes
- [ ] **Mesmo espaçamento**: Proporções similares
- [ ] **Transição suave**: Card → Página não causa "choque visual"

---

## 🔧 Decisões de Design

### 1. Remoção do Chip "PERIÓDICO"

**Razão:**
- Página de detalhe mostra apenas categoria
- Chip "PERIÓDICO" competia visualmente com categoria
- Informação redundante (já está no Journal name)

**Impacto:**
- Card mais limpo
- Foco na categoria (informação mais relevante)
- Alinhamento 100% com página

---

### 2. Ordem dos Metadados

**Nova ordem:** Data • Journal • Idioma • Impacto • DOI

**Razão:**
- Alinhada com página de detalhe
- Facilita reconhecimento visual
- Ordem lógica: temporal → fonte → linguagem → métrica → identificador

**Antes:** Autor • Journal • Data (ordem diferente)

---

### 3. Autores em Linha Separada

**Razão:**
- Página de detalhe tem autores em linha própria
- Facilita scan visual
- Não compete com metadados

**Antes:** Misturado com metadados

---

### 4. DOI como Link Discreto

**Razão:**
- Página de detalhe mostra DOI como link
- Acesso rápido sem precisar abrir página
- Visual discreto (não compete com ações principais)

**Implementação:**
- Link na metadata bar
- Truncado com ellipsis se muito longo
- Cor primária (destaque sutil)

---

### 5. Ações no Topo (Ícones Compactos)

**Razão:**
- Página de detalhe tem action bar com essas ações
- Acesso rápido sem scroll
- Visual compacto (não ocupa muito espaço)

**Ações:**
- Salvar (bookmark)
- Copiar DOI (copy) - apenas se DOI existir
- Compartilhar (share-2)

---

## 📝 Notas de Implementação

### JavaScript

**Funções globais:**
- `window.copyDOI(doi)`: Copia URL do DOI
- `window.shareArticle(id, title)`: Compartilha via Web Share API ou copia URL
- `window.toggleSaveArticle(id)`: Placeholder (implementar conforme necessário)

**Integração:**
- Funções chamadas via `onclick` no template
- Feedback via toast (se disponível) ou console
- Tratamento de erros (clipboard não disponível, etc.)

---

### CSS

**Versão compacta:**
- Classe `.article-card--compact` aplicada condicionalmente
- Reduz padding, altura, espaçamentos
- Mantém hierarquia visual

**Estado ativo:**
- `.is-active` aplicado via `keyboard-shortcuts.js`
- Realce discreto (ring + sombra + background)
- Não altera layout

---

## ✅ Conclusão

Alinhamento 100% implementado:

- ✅ Chip único (categoria apenas)
- ✅ Título: 1 linha mobile, 2 desktop
- ✅ Autores: linha separada "Autor principal et al."
- ✅ Metadados: ordem alinhada (Data • Journal • Idioma • Impacto • DOI)
- ✅ DOI: link discreto
- ✅ Ações no topo: Salvar, Copiar DOI, Compartilhar
- ✅ Ações no rodapé: "Ler original", "Ver detalhes"
- ✅ Estado ativo: `.is-active` com realce discreto
- ✅ Coerência visual: mesma ordem e rótulos da página

O card compacto agora funciona como uma "prévia" direta da página, sem surpresas ao abrir o detalhe.
