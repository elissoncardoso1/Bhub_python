# Sincronização de Duração do Toast - Diffs e Checklist

**Data:** 2026-01-26  
**Status:** ✅ Implementado

---

## 📋 Resumo

Sincronização da duração do toast entre CSS (progress bar) e JavaScript (timeout de remoção) usando variável CSS `--toast-duration` definida dinamicamente pelo JS.

---

## 🎯 Objetivos Alcançados

✅ Progress bar usa variável CSS `--toast-duration`  
✅ JS define variável inline ao criar toast  
✅ Duração sincronizada entre animação e timeout  
✅ Reduced motion não quebra timing  
✅ Progress bar adicionada ao HTML dos toasts

---

## 🔄 Diffs Aplicados

### 1. **animations.css - Variável CSS e Progress Bar**

**Adicionado em `:root`:**
```css
/* Duração de toast - pode ser sobrescrita pelo JS via inline style */
--toast-duration: 5000ms;
```

**Antes:**
```css
.toast-progress {
  animation: toastProgress 5s linear forwards;
}
```

**Depois:**
```css
.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: var(--color-primary-400);
  animation: toastProgress var(--toast-duration, 5000ms) linear forwards;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}
```

**Razão:** 
- Usa variável CSS que pode ser sobrescrita pelo JS
- Fallback de 5000ms se variável não estiver definida
- Estilização melhorada (posição, cor, border-radius)

---

### 2. **animations.css - Reduced Motion para Progress Bar**

**Adicionado em `@media (prefers-reduced-motion: reduce)`:**
```css
/* Progress bar do toast - desabilitar animação mas manter funcionalidade */
.toast-progress {
  animation: none !important;
  width: 100%; /* Mantém barra visível mas não anima */
}
```

**Razão:** 
- Desabilita animação da progress bar em reduced motion
- Mantém barra visível (100% width) para não confundir usuário
- Timeout JS ainda funciona normalmente (toast fecha no tempo correto)

---

### 3. **app.js - showErrorToast Atualizado**

**Antes:**
```javascript
function showErrorToast(message, title = "Erro") {
  const toast = document.createElement("div");
  toast.className = "max-w-sm animate-in slide-in-from-top-5 duration-300";
  toast.innerHTML = `...`;
  
  setTimeout(() => {
    toast.remove();
  }, 5000);
}
```

**Depois:**
```javascript
function showErrorToast(message, title = "Erro", duration = 5000) {
  const toast = document.createElement("div");
  toast.className = "max-w-sm animate-in slide-in-from-top-5 duration-300 relative overflow-hidden";
  
  // Definir duração via CSS variable (sincroniza com progress bar)
  toast.style.setProperty('--toast-duration', duration + 'ms');
  
  toast.innerHTML = `
    ...
    <div class="toast-progress" aria-hidden="true"></div>
  `;
  
  setTimeout(() => {
    toast.remove();
  }, duration);
}
```

**Mudanças:**
- ✅ Parâmetro `duration` adicionado (padrão: 5000ms)
- ✅ Variável CSS `--toast-duration` definida inline
- ✅ Progress bar adicionada ao HTML
- ✅ Classes `relative overflow-hidden` para posicionar progress bar
- ✅ Timeout usa `duration` em vez de hardcoded 5000

---

### 4. **app.js - showSuccessToast Atualizado**

**Mesmas mudanças aplicadas:**
- ✅ Parâmetro `duration` adicionado
- ✅ Variável CSS definida inline
- ✅ Progress bar adicionada
- ✅ Timeout sincronizado

---

## 📊 Sincronização

### Fluxo de Sincronização

1. **JS cria toast:**
   ```javascript
   toast.style.setProperty('--toast-duration', '5000ms');
   ```

2. **CSS usa variável:**
   ```css
   animation: toastProgress var(--toast-duration, 5000ms) linear forwards;
   ```

3. **Progress bar anima:**
   - Duração: `var(--toast-duration)` (5000ms)
   - Animação: `toastProgress` (width 100% → 0%)

4. **JS remove toast:**
   ```javascript
   setTimeout(() => toast.remove(), 5000);
   ```

**Resultado:** Progress bar e timeout JS estão sincronizados! ✅

---

## 🎨 Progress Bar - Estilo

### Características:
- **Posição:** `absolute`, `bottom: 0`, `left: 0`
- **Altura:** `3px`
- **Cor:** `var(--color-primary-400)` (teal)
- **Animação:** `toastProgress` (width 100% → 0%)
- **Duração:** `var(--toast-duration)` (definida pelo JS)
- **Border-radius:** Apenas nas bordas inferiores

### Visual:
```
┌─────────────────────────┐
│  Toast Content          │
│  [X]                    │
├─────────────────────────┤ ← Progress bar (3px, anima de → para ←)
```

---

## ✅ Checklist de Validação

### Sincronização de Duração

- [ ] **Progress Bar e Timeout Sincronizados**
  - [ ] Criar toast de erro
  - [ ] Verificar que progress bar aparece na parte inferior
  - [ ] Verificar que progress bar anima de direita para esquerda
  - [ ] Verificar que toast fecha quando progress bar chega a 0%
  - [ ] Timing deve ser idêntico (sem delay)

- [ ] **Duração Customizável**
  - [ ] Chamar `showErrorToast("Teste", "Título", 3000)`
  - [ ] Verificar que progress bar anima em 3 segundos
  - [ ] Verificar que toast fecha em 3 segundos
  - [ ] Testar com diferentes durações (2000ms, 7000ms, 10000ms)

- [ ] **Duração Padrão**
  - [ ] Chamar `showErrorToast("Teste")` sem especificar duração
  - [ ] Verificar que usa 5000ms (padrão)
  - [ ] Progress bar e timeout devem ser 5 segundos

### Progress Bar Visual

- [ ] **Aparência**
  - [ ] Progress bar visível na parte inferior do toast
  - [ ] Cor teal (`primary-400`)
  - [ ] Altura de 3px
  - [ ] Border-radius nas bordas inferiores
  - [ ] Não sobrepõe conteúdo

- [ ] **Animação**
  - [ ] Animação suave (linear)
  - [ ] Começa em 100% width
  - [ ] Termina em 0% width
  - [ ] Duração correta (sincronizada com timeout)

### Reduced Motion

- [ ] **Com `prefers-reduced-motion: reduce` Ativo**
  - [ ] Ativar reduced motion no DevTools
  - [ ] Criar toast
  - [ ] Verificar que progress bar **não anima**
  - [ ] Verificar que progress bar fica em 100% width (visível)
  - [ ] Verificar que toast **ainda fecha** no tempo correto (timeout JS funciona)
  - [ ] Funcionalidade preservada (apenas animação desabilitada)

### Funcionalidade

- [ ] **Toast de Erro**
  - [ ] `showErrorToast("Mensagem", "Título", 5000)` funciona
  - [ ] Progress bar aparece e anima
  - [ ] Toast fecha automaticamente
  - [ ] Botão de fechar funciona (fecha antes do timeout)

- [ ] **Toast de Sucesso**
  - [ ] `showSuccessToast("Mensagem", "Título", 5000)` funciona
  - [ ] Progress bar aparece e anima
  - [ ] Toast fecha automaticamente
  - [ ] Botão de fechar funciona

- [ ] **Múltiplos Toasts**
  - [ ] Criar vários toasts rapidamente
  - [ ] Cada toast tem sua própria progress bar
  - [ ] Cada progress bar anima independentemente
  - [ ] Cada toast fecha no tempo correto

### Acessibilidade

- [ ] **Progress Bar**
  - [ ] Progress bar tem `aria-hidden="true"` (decorativa)
  - [ ] Não interfere com screen readers
  - [ ] Visualmente clara para usuários

- [ ] **Toast**
  - [ ] `role="alert"` ou `aria-live` correto
  - [ ] Botão de fechar acessível
  - [ ] Focus visível no botão de fechar

---

## 🧪 Como Validar

### 1. Teste de Sincronização Manual

**Procedimento:**
1. Abrir console do navegador
2. Executar: `showErrorToast("Teste de sincronização", "Teste", 5000)`
3. Observar progress bar animando
4. Cronometrar: toast deve fechar exatamente quando progress bar chega a 0%

**O que verificar:**
- ✅ Progress bar anima suavemente
- ✅ Timing sincronizado (sem delay entre animação e fechamento)
- ✅ Toast fecha no momento correto

---

### 2. Teste de Duração Customizável

**Procedimento:**
```javascript
// No console
showErrorToast("3 segundos", "Teste", 3000);
// Verificar que fecha em 3s

showSuccessToast("7 segundos", "Teste", 7000);
// Verificar que fecha em 7s
```

**O que verificar:**
- ✅ Progress bar anima na duração especificada
- ✅ Toast fecha na duração especificada
- ✅ Sincronização mantida

---

### 3. Teste de Reduced Motion

**Procedimento:**
1. DevTools → Rendering → "prefers-reduced-motion: reduce"
2. Recarregar página
3. Criar toast: `showErrorToast("Teste reduced motion")`
4. Observar comportamento

**O que verificar:**
- ✅ Progress bar não anima (fica em 100%)
- ✅ Toast ainda fecha em 5 segundos (timeout JS funciona)
- ✅ Funcionalidade preservada

---

### 4. Teste de Variável CSS

**Procedimento:**
```javascript
// No console, após criar toast
const toast = document.querySelector('[role="alert"]');
getComputedStyle(toast).getPropertyValue('--toast-duration');
// Deve retornar: "5000ms" (ou duração customizada)
```

**O que verificar:**
- ✅ Variável CSS está definida no elemento
- ✅ Valor corresponde à duração especificada

---

### 5. Teste Visual da Progress Bar

**Procedimento:**
1. Criar toast
2. Inspecionar elemento `.toast-progress`
3. Verificar estilos aplicados

**O que verificar:**
- ✅ `position: absolute`
- ✅ `bottom: 0`
- ✅ `height: 3px`
- ✅ `background: var(--color-primary-400)`
- ✅ `animation: toastProgress var(--toast-duration) linear forwards`

---

## 📝 Notas Técnicas

### Variável CSS Inline

**Por que inline style?**
- Permite duração customizável por toast
- Sincroniza com timeout JS
- Mais flexível que valor hardcoded

**Alternativa considerada:**
- Classe CSS com duração específica (ex: `.toast-3s`, `.toast-5s`)
- **Rejeitada:** Menos flexível, requer múltiplas classes

### Reduced Motion

**Comportamento:**
- Animação CSS desabilitada (`animation: none`)
- Progress bar fica em 100% width (visível mas não anima)
- Timeout JS continua funcionando normalmente
- Toast fecha no tempo correto

**Razão:** Usuários com reduced motion ainda precisam saber que toast vai fechar, mas não precisam ver animação.

### Compatibilidade

- ✅ `CSS.setProperty()`: Suportado em todos navegadores modernos
- ✅ CSS Custom Properties: Suportado
- ✅ `prefers-reduced-motion`: Suportado

---

## 🎯 Resultado Final

✅ **Progress bar sincronizada com timeout JS**  
✅ **Duração customizável via parâmetro**  
✅ **Reduced motion não quebra timing**  
✅ **Progress bar visualmente clara**  
✅ **Tokens semânticos usados**  
✅ **Acessibilidade preservada**

---

## 📊 Estatísticas

- ✅ **1 variável CSS** adicionada (`--toast-duration`)
- ✅ **2 funções JS** atualizadas (`showErrorToast`, `showSuccessToast`)
- ✅ **1 progress bar** adicionada ao HTML
- ✅ **1 regra reduced-motion** adicionada para progress bar

---

**Status:** ✅ Sincronização completa. Pronto para testes.
