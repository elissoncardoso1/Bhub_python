# 🎨 Integração Anime.js - BHUB

**Data:** 2025-01-27  
**Status:** ✅ Integrado

---

## 📦 Biblioteca

**Anime.js v3.2.2**
- **CDN:** `https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js`
- **Tamanho:** ~17KB (minificado)
- **Documentação:** https://animejs.com/

---

## 🚀 Funcionalidades Implementadas

### 1. Animações de Cards de Artigos
- **Entrada:** Fade in + translateY + scale
- **Stagger:** Delay progressivo entre cards
- **Hover:** Scale suave no hover

### 2. Animações de Scroll
- **Substitui:** Intersection Observer antigo
- **Tipos disponíveis:**
  - `fadeInUp` (padrão)
  - `fadeInDown`
  - `fadeInScale`
  - `slideInLeft`
  - `slideInRight`

### 3. Animações de Modais
- **Entrada:** Backdrop fade + conteúdo scale
- **Saída:** Fade out suave

### 4. Animações de Toasts
- **Entrada:** Slide in da direita
- **Saída:** Slide out para direita

### 5. Animações de Skeleton Loaders
- **Fade out:** Quando conteúdo real aparece

---

## 📝 Como Usar

### Animações Automáticas

As animações são aplicadas automaticamente aos seguintes elementos:

#### Cards de Artigos
```html
<!-- Automático - não precisa fazer nada -->
<article class="article-card">
  <!-- conteúdo -->
</article>
```

#### Scroll Animations
```html
<!-- Adicione data-anime-type para tipo específico -->
<div class="animate-on-scroll" data-anime-type="fadeInUp">
  Conteúdo que anima ao entrar na viewport
</div>

<!-- Tipos disponíveis -->
<div data-anime-type="fadeInUp">Fade in de baixo</div>
<div data-anime-type="fadeInDown">Fade in de cima</div>
<div data-anime-type="fadeInScale">Fade in com scale</div>
<div data-anime-type="slideInLeft">Slide da esquerda</div>
<div data-anime-type="slideInRight">Slide da direita</div>
```

### Uso Programático

```javascript
// Animar cards manualmente
window.bhubAnimations.animateArticleCards();

// Animar modal
window.bhubAnimations.animateModal(modalElement);

// Animar saída de modal
window.bhubAnimations.animateModalOut(modalElement, callback);

// Animar toast
window.bhubAnimations.animateToast(toastElement);

// Animar lista de cards com stagger
window.bhubAnimations.animateStaggerCards(containerElement);
```

---

## ⚙️ Configuração

### Respeitar prefers-reduced-motion

O sistema automaticamente desabilita animações se o usuário preferir movimento reduzido:

```css
@media (prefers-reduced-motion: reduce) {
  /* Animações desabilitadas automaticamente */
}
```

### Customizar Durações

Edite `app/static/js/animations.js`:

```javascript
anime({
  targets: cards,
  duration: 600,  // Duração em ms
  delay: anime.stagger(100),  // Delay entre elementos
  easing: 'easeOutCubic'  // Tipo de easing
});
```

---

## 🎯 Integração com HTMX

As animações são automaticamente aplicadas após swaps do HTMX:

- **Cards:** Animados após `htmx:afterSwap` no grid de artigos
- **Modais:** Animados quando modal é aberto
- **Hover:** Re-inicializado após cada swap

---

## 📊 Performance

- **Lazy Loading:** Animações só executam quando elementos estão visíveis
- **Debounce:** Evita múltiplas animações simultâneas
- **Fallback:** Funciona mesmo se anime.js não carregar

---

## 🔧 Easing Functions Disponíveis

Anime.js inclui vários easings:

- `linear`
- `easeInQuad`, `easeOutQuad`, `easeInOutQuad`
- `easeInCubic`, `easeOutCubic`, `easeInOutCubic`
- `easeInQuart`, `easeOutQuart`, `easeInOutQuart`
- `easeInQuint`, `easeOutQuint`, `easeInOutQuint`
- `easeInSine`, `easeOutSine`, `easeInOutSine`
- `easeInExpo`, `easeOutExpo`, `easeInOutExpo`
- `easeInCirc`, `easeOutCirc`, `easeInOutCirc`
- `easeInBack`, `easeOutBack`, `easeInOutBack`
- `easeInElastic`, `easeOutElastic`, `easeInOutElastic`
- `easeInBounce`, `easeOutBounce`, `easeInOutBounce`

---

## 📚 Exemplos Avançados

### Animação Customizada

```javascript
// Exemplo: Animação customizada para um elemento
anime({
  targets: '.my-element',
  translateX: [0, 300],
  rotate: [0, 360],
  scale: [1, 1.5],
  duration: 2000,
  easing: 'easeInOutElastic',
  delay: 500
});
```

### Timeline de Animações

```javascript
// Sequência de animações
const tl = anime.timeline({
  easing: 'easeOutExpo',
  duration: 750
});

tl.add({
  targets: '.element1',
  translateX: [0, 300]
}).add({
  targets: '.element2',
  translateY: [0, -100]
}).add({
  targets: '.element3',
  opacity: [0, 1]
});
```

---

## 🐛 Troubleshooting

### Animações não funcionam
1. Verifique se anime.js carregou: `console.log(typeof anime)`
2. Verifique se `prefers-reduced-motion` está desabilitado
3. Verifique console para erros JavaScript

### Performance ruim
1. Reduza número de elementos animados simultaneamente
2. Use `will-change` CSS para elementos animados
3. Considere usar `transform` e `opacity` apenas (GPU accelerated)

---

## 📁 Arquivos Modificados

1. `app/templates/base.html` - Adicionado CDN do anime.js
2. `app/static/js/animations.js` - **NOVO** - Módulo de animações
3. `app/static/js/app.js` - Atualizado `closeModal` para usar anime.js

---

## ✅ Benefícios

- ✨ Animações mais suaves e profissionais
- 🎯 Controle fino sobre timing e easing
- 📱 Melhor performance (GPU accelerated)
- ♿ Respeita `prefers-reduced-motion`
- 🔄 Integração automática com HTMX
- 🎨 Fácil de customizar e estender

---

**Última atualização:** 2025-01-27

