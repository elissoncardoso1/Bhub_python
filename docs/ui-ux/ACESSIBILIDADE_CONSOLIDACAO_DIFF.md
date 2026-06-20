# Consolidação de Acessibilidade - Diffs e Checklist

**Data:** 2026-01-26  
**Status:** ✅ Implementado

---

## 📋 Resumo

Consolidação de regras de acessibilidade eliminando duplicações e ajustando focus styles para evitar outlines inesperados. Garantidos estados de foco consistentes para modais, toasts e menus.

---

## 🔄 Diffs Aplicados

### 1. **accessibility.css - Focus Visible Específico**

**Antes:**
```css
/* Focus Visible - Migrado para Tailwind Ring
 * Use classes: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2
 * no HTML para elementos interativos
 */
```

**Depois:**
```css
/* Focus Visible - Apenas para elementos interativos
 * Evita outlines inesperados em elementos não-interativos
 */
a:focus-visible,
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[role="button"]:focus-visible,
[role="link"]:focus-visible,
[role="menuitem"]:focus-visible,
[tabindex]:not([tabindex="-1"]):focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

**Razão:** Seletor global `*:focus-visible` causava outlines em elementos não-interativos. Agora apenas elementos interativos recebem focus styles.

---

### 2. **accessibility.css - Skip Link Melhorado**

**Antes:**
```css
.skip-to-main {
  background: var(--color-primary-400);
  color: white;
  padding: 8px 16px;
}
```

**Depois:**
```css
.skip-to-main {
  background: var(--color-primary-400);
  color: var(--color-text-primary);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  transition: var(--transition-fast);
}
```

**Razão:** Usa tokens semânticos e melhora estilo visual.

---

### 3. **accessibility.css - Focus States para Modais/Toasts/Menus**

**Adicionado:**
```css
/* MODAIS E TOASTS - Focus States */
#modal-container [role="dialog"]:focus-within {
  outline: none; /* Focus está nos elementos internos */
}

#modal-container button[aria-label*="Fechar"]:focus-visible,
#modal-container button[aria-label*="Close"]:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
  min-width: 44px;
  min-height: 44px;
}

#toast-container button:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* MENUS MOBILE - Focus States */
#mobile-menu-drawer a:focus-visible,
#mobile-menu-drawer button:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

#mobile-search-modal input:focus-visible,
#mobile-search-modal button:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

**Razão:** Garante focus visível e consistente em modais, toasts e menus mobile usando tokens.

---

### 4. **input.css - Remoção de Duplicação `.sr-only`**

**Antes:**
```css
@layer utilities {
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }
}
```

**Depois:**
```css
/* Nota: .sr-only é fornecido pelo Tailwind via output.css
 * e também definido em accessibility.css como fallback
 * Não é necessário duplicar aqui
 */
```

**Razão:** Elimina duplicação. Tailwind já fornece via `output.css` e `accessibility.css` serve como fallback.

---

### 5. **responsive.css - Reduced Motion Consolidado**

**Antes:**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  
  .animate-blob {
    animation: none;
  }
  
  #mobile-menu-overlay,
  #mobile-menu-drawer {
    transition: none;
  }
}
```

**Depois:**
```css
/* Nota: Regra global de prefers-reduced-motion está em animations.css
 * Regras específicas abaixo complementam a regra global
 */

@media (prefers-reduced-motion: reduce) {
  /* Desabilitar animação blob específica */
  .animate-blob {
    animation: none;
  }
  
  /* Menu mobile sem transição */
  #mobile-menu-overlay,
  #mobile-menu-drawer {
    transition: none !important;
  }
  
  /* Scroll suave desabilitado */
  html {
    scroll-behavior: auto !important;
  }
}
```

**Razão:** Remove duplicação da regra global (já em `animations.css`), mantém apenas regras específicas.

---

### 6. **app.css - Reduced Motion Consolidado**

**Antes:**
```css
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
  }
  
  * {
    transition-duration: 0.01ms !important;
  }
}
```

**Depois:**
```css
/* Nota: Regra global está em animations.css
 * Regra específica abaixo complementa
 */
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none !important;
  }
}
```

**Razão:** Remove duplicação da regra global, mantém apenas regra específica para spinner.

---

### 7. **animations.css - Reduced Motion Melhorado**

**Antes:**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  /* ... regras específicas ... */
}
```

**Depois:**
```css
/* ==========================================
   Reduced Motion - FONTE DA VERDADE
   ========================================== */
/* Esta é a regra global consolidada para prefers-reduced-motion
 * Outros arquivos podem ter regras específicas que complementam esta
 */

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  /* Scroll suave desabilitado */
  html {
    scroll-behavior: auto !important;
  }
  
  /* ... regras específicas ... */
  
  /* Animações de modal e toast */
  .modal-overlay-enter,
  .modal-overlay-exit,
  .modal-content-enter,
  .modal-content-exit,
  .toast-enter,
  .toast-exit {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

**Razão:** Adiciona `scroll-behavior` e animações de modal/toast, marca como "FONTE DA VERDADE".

---

## 📊 Resumo de Duplicações Eliminadas

### `.sr-only`
- ✅ **Mantido em:** `accessibility.css` (fonte única para CSS manual)
- ✅ **Fornecido por:** Tailwind via `output.css`
- ❌ **Removido de:** `input.css`

### `prefers-reduced-motion`
- ✅ **Fonte da verdade:** `animations.css` (regra global completa)
- ✅ **Complementos específicos:** 
  - `responsive.css` (menu mobile, blob)
  - `app.css` (spinner)
  - `article-card.css` (cards específicos)
- ❌ **Duplicações removidas:** Regras globais duplicadas

### `focus-visible`
- ✅ **Antes:** Seletor global `*:focus-visible` (causava outlines inesperados)
- ✅ **Depois:** Seletores específicos apenas para elementos interativos
- ✅ **Adicionado:** Focus states para modais, toasts, menus

---

## ✅ Checklist de Validação

### Navegação por Teclado

- [ ] **Tab Navigation**
  - [ ] Pressionar `Tab` navega apenas entre elementos interativos
  - [ ] Nenhum elemento não-interativo recebe foco
  - [ ] Ordem lógica de navegação
  - [ ] Nenhum elemento fica "preso"

- [ ] **Focus Visível**
  - [ ] Apenas elementos interativos mostram outline
  - [ ] Outline tem cor `primary-400` (teal)
  - [ ] Outline tem offset de 2px
  - [ ] Outline aparece apenas com teclado (não com mouse)
  - [ ] Border-radius aplicado onde apropriado

- [ ] **Skip Link**
  - [ ] Pressionar `Tab` no início da página mostra skip link
  - [ ] Skip link é visível quando focado
  - [ ] Skip link leva ao conteúdo principal
  - [ ] Estilo visual adequado (cor, padding, border-radius)

### Modais

- [ ] **Abertura**
  - [ ] Modal abre ao ativar trigger
  - [ ] Foco move para primeiro elemento focável no modal
  - [ ] Focus trap funciona (Tab não sai do modal)

- [ ] **Navegação Dentro do Modal**
  - [ ] Tab navega entre elementos do modal
  - [ ] Shift+Tab navega em reverso
  - [ ] Botão de fechar recebe foco corretamente
  - [ ] Focus visível em todos os elementos

- [ ] **Fechamento**
  - [ ] ESC fecha o modal
  - [ ] Botão de fechar funciona
  - [ ] Foco retorna para elemento que abriu o modal
  - [ ] Focus trap é removido

### Toasts

- [ ] **Exibição**
  - [ ] Toast aparece quando disparado
  - [ ] Botão de fechar (se houver) recebe foco
  - [ ] Focus visível no botão de fechar

- [ ] **Interação**
  - [ ] Botão de fechar funciona
  - [ ] Toast fecha ao clicar/focar e ativar botão

### Menus Mobile

- [ ] **Menu Drawer**
  - [ ] Abre ao ativar botão
  - [ ] Tab navega entre links do menu
  - [ ] Focus visível em todos os links
  - [ ] ESC fecha o menu
  - [ ] Foco retorna para botão que abriu

- [ ] **Search Modal**
  - [ ] Abre ao ativar botão
  - [ ] Input recebe foco automaticamente
  - [ ] Focus visível no input
  - [ ] Botões dentro do modal têm focus visível
  - [ ] ESC fecha o modal

### Reduced Motion

- [ ] **Com `prefers-reduced-motion: reduce` Ativo**
  - [ ] Todas as animações desabilitadas
  - [ ] Todas as transições instantâneas
  - [ ] Scroll suave desabilitado
  - [ ] Spinner para de animar
  - [ ] Menu mobile sem transição
  - [ ] Modais aparecem instantaneamente
  - [ ] Toasts aparecem instantaneamente
  - [ ] Cards não animam

- [ ] **Funcionalidade Preservada**
  - [ ] Modais ainda abrem/fecham
  - [ ] Toasts ainda aparecem
  - [ ] Menus ainda funcionam
  - [ ] Apenas animações são desabilitadas

### Screen Reader

- [ ] **`.sr-only` Funciona**
  - [ ] Elementos com `.sr-only` são ocultos visualmente
  - [ ] Screen reader anuncia conteúdo de `.sr-only`
  - [ ] Sem regressões visuais

- [ ] **ARIA Labels**
  - [ ] Modais têm `role="dialog"` e `aria-labelledby`
  - [ ] Toasts têm `role="alert"` ou `aria-live`
  - [ ] Botões têm `aria-label` quando necessário
  - [ ] Menus têm `aria-expanded` correto

### Consistência Visual

- [ ] **Focus Styles Consistentes**
  - [ ] Todos os elementos interativos têm mesmo estilo de focus
  - [ ] Cor: `primary-400` (teal)
  - [ ] Espessura: 2px
  - [ ] Offset: 2px
  - [ ] Border-radius aplicado consistentemente

- [ ] **Tokens Semânticos**
  - [ ] Todos os focus styles usam `var(--color-primary-400)`
  - [ ] Espaçamentos usam tokens `--space-*`
  - [ ] Radius usam tokens `--radius-*`

---

## 🧪 Como Validar

### 1. Teste de Navegação por Teclado

**Procedimento:**
1. Abrir página
2. Pressionar `Tab` repetidamente
3. Verificar que apenas elementos interativos recebem foco
4. Verificar que outline aparece apenas com teclado
5. Verificar ordem lógica de navegação

**O que verificar:**
- ✅ Links, botões, inputs recebem foco
- ❌ Textos, imagens, divs não recebem foco
- ✅ Outline visível e consistente

---

### 2. Teste de Skip Link

**Procedimento:**
1. Recarregar página
2. Imediatamente pressionar `Tab`
3. Verificar que skip link aparece no topo
4. Pressionar `Enter` no skip link
5. Verificar que foco vai para `#main-content`

**O que verificar:**
- ✅ Skip link visível quando focado
- ✅ Skip link funciona
- ✅ Estilo visual adequado

---

### 3. Teste de Modal

**Procedimento:**
1. Abrir modal (se houver trigger)
2. Verificar que foco vai para primeiro elemento
3. Pressionar `Tab` várias vezes
4. Verificar que foco não sai do modal (focus trap)
5. Pressionar `ESC`
6. Verificar que modal fecha e foco retorna

**O que verificar:**
- ✅ Focus trap funciona
- ✅ Botão de fechar tem focus visível
- ✅ ESC fecha modal
- ✅ Foco retorna corretamente

---

### 4. Teste de Toast

**Procedimento:**
1. Disparar toast (via JS ou ação)
2. Verificar que toast aparece
3. Se houver botão de fechar, focar nele
4. Verificar focus visível
5. Ativar botão (Enter/Space)

**O que verificar:**
- ✅ Toast aparece
- ✅ Botão de fechar tem focus visível
- ✅ Botão funciona

---

### 5. Teste de Menu Mobile

**Procedimento:**
1. Redimensionar para mobile (<640px) ou usar DevTools
2. Clicar no botão de menu mobile
3. Verificar que drawer abre
4. Pressionar `Tab` para navegar entre links
5. Verificar focus visível
6. Pressionar `ESC`
7. Verificar que menu fecha

**O que verificar:**
- ✅ Drawer abre
- ✅ Links têm focus visível
- ✅ ESC fecha menu
- ✅ Foco retorna para botão

---

### 6. Teste de Reduced Motion

**Procedimento:**
1. Abrir DevTools → Rendering
2. Ativar "prefers-reduced-motion: reduce"
3. Recarregar página
4. Interagir com elementos (abrir modais, toasts, menus)
5. Verificar que não há animações

**O que verificar:**
- ✅ Nenhuma animação visível
- ✅ Transições instantâneas
- ✅ Modais aparecem instantaneamente
- ✅ Funcionalidade preservada

---

### 7. Teste com Screen Reader (Básico)

**Procedimento:**
1. Usar leitor de tela (NVDA, JAWS, VoiceOver)
2. Navegar com teclado
3. Verificar que elementos são anunciados corretamente
4. Verificar que `.sr-only` é lido mas não visível

**O que verificar:**
- ✅ Elementos interativos são anunciados
- ✅ Skip link é anunciado
- ✅ Modais são anunciados como dialogs
- ✅ Toasts são anunciados como alerts

---

## 📝 Notas Técnicas

### Hierarquia de Reduced Motion

1. **Global:** `animations.css` (fonte da verdade)
2. **Específicos:** 
   - `responsive.css` (menu mobile, blob)
   - `app.css` (spinner)
   - `article-card.css` (cards)

**Razão:** Regra global cobre tudo, regras específicas complementam quando necessário.

### Focus Visible - Por Que Específico?

**Problema com `*:focus-visible`:**
- Causava outlines em elementos não-interativos
- Podia aparecer em divs, spans, etc.
- Confundia usuários

**Solução:**
- Seletores específicos apenas para elementos interativos
- Lista explícita de elementos que devem ter focus
- Mais controle e previsibilidade

### Compatibilidade

- ✅ `:focus-visible`: Suportado em navegadores modernos
- ✅ `prefers-reduced-motion`: Suportado
- ✅ CSS Custom Properties: Suportado

---

## 🎯 Resultado Final

✅ **Duplicações eliminadas**  
✅ **Focus styles específicos e consistentes**  
✅ **Modais/toasts/menus com focus states**  
✅ **Reduced motion consolidado**  
✅ **Tokens semânticos usados**  
✅ **Acessibilidade melhorada**

---

**Status:** ✅ Consolidação completa. Pronto para testes.
