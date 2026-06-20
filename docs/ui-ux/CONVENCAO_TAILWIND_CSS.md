# 📋 Convenção: Tailwind vs CSS Manual

**Data:** 2026-01-26  
**Status:** ✅ Ativo

---

## 🎯 Princípio Geral

Este projeto usa uma **abordagem híbrida**:
- **Tailwind CSS** para layout e utilitários
- **CSS Manual** para componentes reutilizáveis e lógica complexa

---

## ✅ Tailwind CSS (output.css)

### Quando Usar

✅ **Layout e Estrutura:**
- Flexbox/Grid: `flex`, `grid`, `flex-col`, `grid-cols-2`
- Espaçamento: `gap-4`, `space-y-2`, `p-4`, `m-2`
- Posicionamento: `absolute`, `relative`, `sticky`, `fixed`
- Dimensões: `w-full`, `h-screen`, `max-w-sm`

✅ **Utilitários Visuais:**
- Bordas: `rounded-lg`, `border`, `border-gray-300`
- Sombras: `shadow-sm`, `shadow-lg`
- Cores utilitárias: `bg-white`, `text-gray-600`
- Opacidade: `opacity-50`, `opacity-75`

✅ **Responsividade:**
- Breakpoints: `sm:`, `md:`, `lg:`, `xl:`
- Exemplo: `md:flex lg:grid-cols-3`

✅ **Estados Simples:**
- Hover: `hover:bg-gray-100`
- Focus: `focus:outline-none`
- Active: `active:scale-95`

### Quando NÃO Usar

❌ Componentes reutilizáveis (`.btn`, `.card`, `.badge`)  
❌ Lógica complexa de estados (`.btn.primary:hover`)  
❌ Animações customizadas  
❌ Acessibilidade (focus-visible, reduced-motion)  
❌ Design tokens (use `var(--color-*)`)

---

## ✅ CSS Manual (app.css, article-card.css, etc.)

### Quando Usar

✅ **Componentes Reutilizáveis:**
- `.btn`, `.card`, `.badge`, `.panel`, `.toast`
- `.article-card`, `.site-header`

✅ **Estados Complexos:**
- `.btn.primary:hover`
- `.card.is-active`
- `.badge.ok`

✅ **Design Tokens:**
- `var(--color-*)` (cores semânticas)
- `var(--space-*)` (espaçamento)
- `var(--font-*)` (tipografia)
- `var(--radius-*)` (bordas)
- `var(--shadow-*)` (sombras)

✅ **Acessibilidade:**
- `:focus-visible` (focus visível)
- `@media (prefers-reduced-motion)` (reduced motion)
- `.sr-only` (screen reader only)

✅ **Animações:**
- `@keyframes` customizados
- Transitions complexas

### Quando NÃO Usar

❌ Layout simples (use Tailwind: `flex`, `grid`, `gap`)  
❌ Espaçamento simples (use Tailwind: `p-4`, `m-2`)  
❌ Cores hardcoded (use tokens: `var(--color-*)`)

---

## 📐 Especificidade e Conflitos

### Regra Geral

**Componentes CSS têm prioridade sobre Tailwind utilities.**

### Exemplos

```html
<!-- ✅ Correto: Componente CSS ganha -->
<button class="btn bg-red-500">
  <!-- .btn sobrescreve bg-red-500 (background) -->
</button>

<!-- ✅ Correto: Propriedades diferentes -->
<div class="card p-4">
  <!-- .card define background/border, p-4 define padding -->
</div>

<!-- ✅ Correto: Especificidade suficiente -->
<button class="btn btn-primary">
  <!-- .btn.primary (0,2,0) ganha sobre utilities -->
</button>
```

### Aumentando Especificidade

Se houver conflito, aumentar especificidade do componente:

```css
/* ✅ Bom: Especificidade 0,2,0 */
.btn.primary {
  background: var(--app-brand);
}

/* ✅ Melhor: Especificidade 0,2,0 (mais explícito) */
.btn.btn-primary {
  background: var(--app-brand);
}

/* ❌ Evitar: !important (exceto reduced-motion) */
.btn {
  background: var(--app-panel) !important;
}
```

---

## 🎨 Design Tokens

### Fonte da Verdade

**`design-tokens.css`** é a única fonte de verdade para:
- Cores: `--color-*`
- Espaçamento: `--space-*`
- Tipografia: `--font-*`, `--line-height-*`
- Bordas: `--radius-*`
- Sombras: `--shadow-*`
- Transições: `--transition-*`

### Uso Correto

```css
/* ✅ Correto: Usar tokens */
.btn {
  background: var(--color-bg-primary);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
}

/* ❌ Errado: Hardcoded */
.btn {
  background: #ffffff;
  padding: 8px 12px;
  border-radius: 8px;
  color: #0b3536;
}
```

---

## 📁 Estrutura de Arquivos

```
app/static/css/
├── design-tokens.css  → Tokens semânticos (fonte da verdade)
├── app.css            → Componentes genéricos (.btn, .card, .badge)
├── article-card.css   → Componente específico (.article-card)
├── accessibility.css  → Regras de acessibilidade
├── animations.css     → Animações e reduced-motion
├── responsive.css     → Media queries específicas
├── input.css          → Source do Tailwind (@tailwind directives)
└── output.css         → Tailwind compilado (gerado automaticamente)
```

### Ordem de Carregamento (base.html)

```html
1. design-tokens.css    → Tokens primeiro
2. accessibility.css    → Acessibilidade
3. responsive.css       → Responsividade
4. animations.css       → Animações
5. article-card.css     → Componentes específicos
6. output.css           → Tailwind (pode sobrescrever utilities)
7. app.css              → Componentes genéricos (maior especificidade)
```

---

## 🔧 Guia de Manutenção

### Adicionar Novo Componente

**Pergunta:** É reutilizável e tem lógica complexa?

- ✅ **Sim** → Criar em `app.css` ou arquivo específico
- ❌ **Não** → Usar Tailwind no HTML

**Exemplo:**
```css
/* app.css */
.my-component {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  padding: var(--space-4);
}

.my-component.is-active {
  border-color: var(--color-primary-400);
}
```

```html
<!-- HTML -->
<div class="my-component flex items-center gap-2">
  <!-- Tailwind para layout, CSS para componente -->
</div>
```

---

### Mudar Cor/Espaço

**Sempre em:** `design-tokens.css`

```css
/* design-tokens.css */
:root {
  --color-primary-400: #3fb5a3; /* Mudar aqui */
  --space-4: 1rem; /* Mudar aqui */
}
```

**Nunca hardcode em componentes!**

---

### Ajustar Layout

**Usar Tailwind no HTML:**

```html
<!-- ✅ Correto -->
<div class="flex flex-col gap-4 md:flex-row lg:grid lg:grid-cols-3">
  <!-- Layout com Tailwind -->
</div>
```

**Não criar classes CSS para layout simples!**

---

### Resolver Conflito de Especificidade

**Problema:** Tailwind utility sobrescreve componente CSS

**Solução 1:** Aumentar especificidade do componente
```css
/* Antes: .btn (0,1,0) */
.btn {
  background: var(--app-panel);
}

/* Depois: .btn.btn (0,2,0) */
.btn.btn {
  background: var(--app-panel);
}
```

**Solução 2:** Usar seletores mais específicos
```css
/* Antes */
.btn {
  background: var(--app-panel);
}

/* Depois */
button.btn,
a.btn {
  background: var(--app-panel);
}
```

**Solução 3:** Reorganizar ordem de carregamento (último recurso)

---

## ✅ Checklist de Validação

### Antes de Adicionar CSS Manual

- [ ] É um componente reutilizável?
- [ ] Tem lógica complexa de estados?
- [ ] Precisa de acessibilidade específica?
- [ ] Usa design tokens?

### Antes de Usar Tailwind

- [ ] É layout simples?
- [ ] É utilitário visual?
- [ ] É responsividade?
- [ ] Não conflita com componentes CSS?

### Antes de Commitar

- [ ] Não há cores hardcoded?
- [ ] Não há espaçamento hardcoded?
- [ ] Especificidade é suficiente?
- [ ] Design tokens são usados?

---

## 📚 Exemplos Práticos

### Exemplo 1: Botão com Layout Tailwind

```html
<!-- ✅ Correto -->
<button class="btn btn-primary flex items-center gap-2">
  <svg class="w-5 h-5">...</svg>
  <span>Clique aqui</span>
</button>
```

- `.btn.btn-primary` → CSS (componente, estados)
- `flex items-center gap-2` → Tailwind (layout)

---

### Exemplo 2: Card com Responsividade

```html
<!-- ✅ Correto -->
<article class="card grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="card-title">Título</div>
  <div class="card-meta">Meta</div>
</article>
```

- `.card`, `.card-title`, `.card-meta` → CSS (componente)
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4` → Tailwind (layout responsivo)

---

### Exemplo 3: Badge com Estado

```html
<!-- ✅ Correto -->
<span class="badge badge-ok flex items-center gap-1">
  <svg class="w-4 h-4">...</svg>
  <span>OK</span>
</span>
```

- `.badge.badge-ok` → CSS (componente, estado)
- `flex items-center gap-1` → Tailwind (layout)

---

## 🎯 Resumo

| Aspecto | Tailwind | CSS Manual |
|---------|----------|------------|
| **Layout** | ✅ | ❌ |
| **Utilitários** | ✅ | ❌ |
| **Componentes** | ❌ | ✅ |
| **Estados Complexos** | ❌ | ✅ |
| **Design Tokens** | ❌ | ✅ |
| **Acessibilidade** | ❌ | ✅ |
| **Animações** | ❌ | ✅ |

---

**Última atualização:** 2026-01-26  
**Mantido por:** Equipe UI/UX
