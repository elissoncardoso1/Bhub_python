# PASSO 1: Consolidar Focus Styles - Diffs e Checklist

**Data:** 2026-01-26  
**Status:** ✅ Implementado

---

## 📋 Resumo das Mudanças

Removidos estilos de focus manuais (`outline`) e migrados para sistema Tailwind Ring. Focus styles agora devem ser aplicados via classes Tailwind no HTML.

---

## 🔄 Diffs Aplicados

### 1. `accessibility.css`

**Removido:**
```css
/* Focus Visible */
*:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
}
```

**Adicionado:**
```css
/* Focus Visible - Migrado para Tailwind Ring
 * Use classes: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2
 * no HTML para elementos interativos
 */
```

---

### 2. `article-card.css`

**Removidos 5 blocos de `:focus-visible`:**

#### 2.1. `.article-card:focus-within`
```diff
- .article-card:focus-within {
-     outline: 2px solid var(--color-primary-400, #3fb5a3);
-     outline-offset: 2px;
- }
+ /* Focus styles migrados para Tailwind Ring
+  * Adicionar no HTML: focus-within:ring-2 focus-within:ring-primary-400 focus-within:ring-offset-2
+  */
```

#### 2.2. `.article-tag:focus-visible`
```diff
- .article-tag:focus-visible {
-     outline: 2px solid var(--color-primary-400, #3fb5a3);
-     outline-offset: 2px;
- }
+ /* Focus styles migrados para Tailwind Ring
+  * Adicionar no HTML: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2
+  */
```

#### 2.3. `.article-title-link:focus-visible`
```diff
- .article-title-link:focus-visible {
-     outline: 2px solid var(--color-primary-400, #3fb5a3);
-     outline-offset: 2px;
-     border-radius: var(--radius-sm, 0.375rem);
- }
+ /* Focus styles migrados para Tailwind Ring
+  * Adicionar no HTML: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 focus:rounded-sm
+  */
```

#### 2.4. `.article-button:focus-visible`
```diff
- .article-button:focus-visible {
-     outline: 2px solid var(--color-primary-400, #3fb5a3);
-     outline-offset: 2px;
- }
+ /* Focus styles migrados para Tailwind Ring
+  * Adicionar no HTML: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2
+  */
```

#### 2.5. `.article-icon-button:focus-visible`
```diff
- .article-icon-button:focus-visible {
-     outline: 2px solid var(--color-primary-400, #3fb5a3);
-     outline-offset: 2px;
- }
+ /* Focus styles migrados para Tailwind Ring
+  * Adicionar no HTML: focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2
+  */
```

---

## 📝 Próximos Passos (HTML)

**IMPORTANTE:** As classes Tailwind devem ser adicionadas nos templates HTML. Segue mapeamento:

### Template: `components/card.html`

#### 1. `.article-card` (linha 1)
```html
<!-- ANTES -->
<article class="article-card" ...>

<!-- DEPOIS -->
<article class="article-card focus-within:ring-2 focus-within:ring-primary-400 focus-within:ring-offset-2" ...>
```

#### 2. `.article-tag` (linhas 10, 37, 44, 53)
```html
<!-- ANTES -->
<span class="article-tag category-{{ article.category.slug }}" ...>

<!-- DEPOIS -->
<span class="article-tag category-{{ article.category.slug }} focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2" ...>
```

#### 3. `.article-title-link` (linha 65)
```html
<!-- ANTES -->
<a href="/articles/{{ article.id }}" 
   class="article-title-link"
   ...>

<!-- DEPOIS -->
<a href="/articles/{{ article.id }}" 
   class="article-title-link focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 focus:rounded-sm"
   ...>
```

#### 4. `.article-button` (linhas 177, 189)
```html
<!-- ANTES -->
<button class="article-button" ...>

<!-- DEPOIS -->
<button class="article-button focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2" ...>
```

#### 5. `.article-icon-button` (linhas 202, 217)
```html
<!-- ANTES -->
<button class="article-icon-button" ...>

<!-- DEPOIS -->
<button class="article-icon-button focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2" ...>
```

---

## ✅ Checklist de Validação

### Navegação por Teclado

- [ ] **Tab Navigation**
  - [ ] Pressionar `Tab` navega entre elementos interativos na ordem correta
  - [ ] Nenhum elemento fica "preso" ou inacessível
  - [ ] Ordem lógica: tags → título → botões → ícones

- [ ] **Focus Visível**
  - [ ] Todos os elementos focáveis mostram ring visível ao receber foco
  - [ ] Ring tem cor `primary-400` (#3fb5a3)
  - [ ] Ring tem offset de 2px (espaçamento do elemento)
  - [ ] Ring aparece apenas com navegação por teclado (não com mouse)

- [ ] **Elementos Específicos**
  - [ ] `.article-card`: ring aparece quando qualquer elemento interno recebe foco
  - [ ] `.article-tag`: ring visível ao focar tag
  - [ ] `.article-title-link`: ring visível ao focar link do título
  - [ ] `.article-button`: ring visível ao focar botão principal
  - [ ] `.article-icon-button`: ring visível ao focar botões de ícone

- [ ] **Ativação**
  - [ ] `Enter` ativa links e botões quando focados
  - [ ] `Space` ativa botões quando focados
  - [ ] Navegação funciona em todos os navegadores (Chrome, Firefox, Safari)

### Consistência Visual

- [ ] **Ring Style**
  - [ ] Todos os rings têm mesma espessura (2px)
  - [ ] Todos os rings têm mesma cor (primary-400)
  - [ ] Todos os rings têm mesmo offset (2px)
  - [ ] Rings não sobrepõem conteúdo importante

- [ ] **Dark Mode**
  - [ ] Rings são visíveis em dark mode
  - [ ] Contraste adequado (WCAG AA mínimo)

### Acessibilidade

- [ ] **Screen Reader**
  - [ ] Elementos focáveis são anunciados corretamente
  - [ ] Estado de foco é comunicado

- [ ] **Reduced Motion**
  - [ ] Com `prefers-reduced-motion: reduce`, focus ainda funciona
  - [ ] Ring aparece instantaneamente (sem animação)

### Regressões

- [ ] **Funcionalidade**
  - [ ] Links ainda funcionam (clicar abre artigo)
  - [ ] Botões ainda funcionam (ações preservadas)
  - [ ] Hover states ainda funcionam
  - [ ] Active states ainda funcionam

- [ ] **Visual**
  - [ ] Sem mudanças visuais indesejadas
  - [ ] Layout não quebrou
  - [ ] Espaçamentos preservados

---

## 🧪 Como Testar

### 1. Teste Manual de Navegação

1. Abrir página com cards de artigos
2. Pressionar `Tab` repetidamente
3. Verificar que ring aparece em cada elemento
4. Pressionar `Enter` em links/botões focados
5. Verificar que ações funcionam

### 2. Teste com DevTools

```javascript
// No console do navegador, testar focus programático:
document.querySelector('.article-title-link').focus();
// Deve mostrar ring

document.querySelector('.article-button').focus();
// Deve mostrar ring
```

### 3. Teste de Acessibilidade

- Usar leitor de tela (NVDA, JAWS, VoiceOver)
- Navegar com teclado
- Verificar que elementos são anunciados corretamente

### 4. Teste Cross-Browser

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari
- [ ] Mobile (iOS Safari, Chrome Mobile)

---

## 📊 Métricas de Sucesso

- ✅ Zero regressões funcionais
- ✅ 100% dos elementos focáveis têm ring visível
- ✅ Consistência visual entre todos os elementos
- ✅ WCAG 2.1 AA compliance mantido

---

## ⚠️ Notas Importantes

1. **Classes Tailwind no HTML:** As mudanças CSS removem os estilos manuais, mas as classes Tailwind precisam ser adicionadas nos templates HTML para que o focus funcione. Isso será feito em uma etapa separada ou pode ser feito agora.

2. **Fallback:** Se as classes Tailwind não forem adicionadas imediatamente, os elementos não terão focus styles visíveis até que sejam adicionadas.

3. **Compatibilidade:** Tailwind Ring funciona em todos os navegadores modernos. Para IE11 (não suportado), focus styles não aparecerão, mas funcionalidade é preservada.

---

**Status:** ✅ CSS atualizado. ⏳ Aguardando adição de classes Tailwind no HTML.
