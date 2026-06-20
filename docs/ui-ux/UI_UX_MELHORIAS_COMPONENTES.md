# Melhorias de Componentes - BHUB
## Sugestões específicas baseadas em análise MCP UI-Expert

**Data:** 2025-01-27  
**Componente analisado:** Article Card

---

## 🎯 Melhorias Recomendadas para Article Card

### 1. Acessibilidade (ARIA Labels)

**Problema atual:**
- Alguns botões têm `aria-label`, mas não todos
- Falta de `role` em alguns elementos
- Navegação por teclado incompleta

**Melhorias:**

```html
<!-- ANTES -->
<button class="article-icon-button" aria-label="Salvar artigo">
    <span class="icon icon-svg">...</span>
</button>

<!-- DEPOIS -->
<button 
    type="button"
    class="article-icon-button" 
    aria-label="Salvar artigo para leitura posterior"
    aria-pressed="false"
    role="button"
    tabindex="0"
    onclick="toggleSaveArticle({{ article.id }})"
    onkeydown="handleKeyDown(event, () => toggleSaveArticle({{ article.id }}))"
>
    <span class="icon icon-svg" aria-hidden="true">...</span>
    <span class="sr-only">Salvar artigo</span>
</button>
```

**Melhorias adicionais:**
- Adicionar `role="article"` no elemento `<article>`
- Adicionar `aria-describedby` para descrever o card
- Implementar `aria-live` para mudanças dinâmicas

---

### 2. Contraste de Cores

**Problema atual:**
- Alguns textos podem não ter contraste suficiente
- Cores de tags podem ser difíceis de ler

**Melhorias:**

```css
/* ANTES */
.article-tag {
    background: rgba(20, 184, 166, 0.15);
    color: #0d7377;
}

/* DEPOIS - Garantir contraste WCAG AA */
.article-tag {
    background: rgba(20, 184, 166, 0.2);  /* Aumentar opacidade */
    color: #0d7377;  /* Verificar: contraste 4.5:1 mínimo */
    border: 1px solid rgba(20, 184, 166, 0.3);  /* Adicionar borda para contraste */
}

/* Verificar contraste com ferramenta: */
/* https://webaim.org/resources/contrastchecker/ */
```

**Cores recomendadas (WCAG AA):**
- Texto em fundo claro: mínimo `#374151` (gray-700)
- Texto em fundo escuro: mínimo `#f3f4f6` (gray-100)
- Links: `#10908d` (primary-500) ou mais escuro

---

### 3. Navegação por Teclado

**Problema atual:**
- Falta de suporte completo para navegação por teclado
- Modais não capturam foco corretamente

**Melhorias:**

```javascript
// Adicionar ao app.js
function handleKeyDown(event, callback) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        callback();
    }
}

// Focus trap para modais
function trapFocus(modalElement) {
    const focusableElements = modalElement.querySelectorAll(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    modalElement.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    });
}
```

---

### 4. Estados de Loading

**Problema atual:**
- Falta feedback visual durante carregamento
- Não há skeleton loaders

**Melhorias:**

```html
<!-- Skeleton Loader -->
<div class="article-card-skeleton" aria-label="Carregando artigo...">
    <div class="skeleton-tags">
        <div class="skeleton skeleton-tag"></div>
        <div class="skeleton skeleton-tag"></div>
    </div>
    <div class="skeleton skeleton-title"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-metrics"></div>
</div>

<style>
.skeleton {
    background: linear-gradient(
        90deg,
        #f0f0f0 25%,
        #e0e0e0 50%,
        #f0f0f0 75%
    );
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
    border-radius: 4px;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-tag {
    width: 80px;
    height: 24px;
}

.skeleton-title {
    width: 100%;
    height: 24px;
    margin-bottom: 12px;
}

.skeleton-text {
    width: 100%;
    height: 16px;
    margin-bottom: 8px;
}

.skeleton-metrics {
    width: 100%;
    height: 60px;
}
</style>
```

---

### 5. Responsividade Mobile

**Problema atual:**
- Cards podem quebrar em telas pequenas
- Touch targets podem ser pequenos

**Melhorias:**

```css
/* Garantir touch targets mínimos (44x44px) */
.article-button,
.article-icon-button {
    min-width: 44px;
    min-height: 44px;
    padding: 12px;  /* Aumentar padding em mobile */
}

/* Melhorar espaçamento em mobile */
@media (max-width: 640px) {
    .article-card {
        padding: 12px;
        min-height: auto;  /* Remover altura mínima fixa */
    }
    
    .article-metrics {
        grid-template-columns: 1fr;  /* Stack em mobile */
        gap: 8px;
    }
    
    .article-footer {
        flex-direction: column;  /* Stack botões em mobile */
        gap: 8px;
    }
    
    .article-button {
        width: 100%;  /* Botão full-width em mobile */
    }
}

/* Melhorar legibilidade em mobile */
@media (max-width: 640px) {
    .article-title {
        font-size: 16px;  /* Aumentar tamanho mínimo */
        line-height: 1.4;
    }
    
    .article-description {
        font-size: 14px;
        line-height: 1.5;
    }
}
```

---

## 📋 Checklist de Implementação

### Acessibilidade
- [ ] Adicionar `aria-label` em todos os botões
- [ ] Adicionar `role` apropriado em elementos
- [ ] Implementar navegação por teclado
- [ ] Adicionar `aria-live` para mudanças dinâmicas
- [ ] Verificar contraste de cores (WCAG AA)
- [ ] Testar com leitores de tela

### Performance
- [ ] Adicionar skeleton loaders
- [ ] Implementar lazy loading de imagens
- [ ] Otimizar CSS (remover estilos não usados)
- [ ] Adicionar `loading="lazy"` em imagens

### Responsividade
- [ ] Garantir touch targets mínimos (44x44px)
- [ ] Testar em dispositivos reais
- [ ] Melhorar layout em telas pequenas
- [ ] Ajustar tipografia para mobile

### UX
- [ ] Adicionar estados de hover mais claros
- [ ] Melhorar feedback de ações
- [ ] Adicionar transições suaves
- [ ] Implementar toast notifications

---

## 🎨 Exemplo de Card Melhorado

```html
<article 
    class="article-card" 
    itemscope 
    itemtype="https://schema.org/ScholarlyArticle"
    role="article"
    aria-labelledby="article-title-{{ article.id }}"
    aria-describedby="article-description-{{ article.id }}"
>
    <!-- Tags com melhor contraste -->
    <div class="article-tags" role="list" aria-label="Categorias do artigo">
        {% if article.category %}
        <span 
            class="article-tag category-{{ article.category.slug }}"
            role="listitem"
            aria-label="Categoria: {{ article.category.name }}"
        >
            <span class="icon icon-svg" aria-hidden="true">...</span>
            <span>{{ article.category.name }}</span>
        </span>
        {% endif %}
    </div>

    <!-- Título com ID para aria-labelledby -->
    <h3 class="article-title" id="article-title-{{ article.id }}">
        <a 
            href="/articles/{{ article.id }}" 
            hx-get="/articles/{{ article.id }}" 
            hx-target="#modal-container" 
            hx-swap="innerHTML"
            hx-push-url="true"
            class="article-title-link"
            itemprop="headline"
            aria-label="Ver detalhes do artigo: {{ article.title_translated or article.title }}"
        >
            {{ article.title_translated or article.title }}
        </a>
    </h3>

    <!-- Metadata com melhor estrutura -->
    <div class="article-metadata" role="list" aria-label="Informações do artigo">
        <div class="metadata-item" role="listitem" itemprop="author" itemscope itemtype="https://schema.org/Person">
            <span class="icon icon-svg" aria-hidden="true">...</span>
            <span itemprop="name">
                {% if article.authors %}
                    {{ article.authors|map(attribute='name')|join(', ') }}
                {% else %}
                    Não informado
                {% endif %}
            </span>
        </div>
    </div>

    <!-- Descrição com ID para aria-describedby -->
    {% if article.abstract_translated or article.abstract %}
    <p 
        class="article-description" 
        id="article-description-{{ article.id }}"
        itemprop="description"
    >
        {{ article.abstract_translated or article.abstract }}
    </p>
    {% endif %}

    <!-- Métricas com melhor acessibilidade -->
    <div class="article-metrics" role="group" aria-label="Métricas do artigo">
        <div class="metric-card impact-card" role="status" aria-label="Score de impacto: {{ article.impact_score|format_float(1) }} de 10">
            <div class="metric-label">
                <span class="icon icon-svg" aria-hidden="true">...</span>
                <span>Impact</span>
            </div>
            <div class="metric-value">
                {{ article.impact_score|format_float(1) }}
                <span class="metric-unit">/10</span>
            </div>
            <div class="metric-bar" role="progressbar" aria-valuenow="{{ article.impact_score|float }}" aria-valuemin="0" aria-valuemax="10" aria-label="Score de impacto">
                <div class="metric-bar-fill" style="width: {{ ((article.impact_score|float / 10 * 100)|round(0))|int }}%"></div>
            </div>
        </div>
    </div>

    <!-- Footer com botões acessíveis -->
    <div class="article-footer" role="group" aria-label="Ações do artigo">
        <a 
            href="/articles/{{ article.id }}" 
            class="article-button"
            hx-get="/articles/{{ article.id }}"
            hx-target="#modal-container"
            hx-swap="innerHTML"
            hx-push-url="true"
            aria-label="Ver detalhes completos do artigo"
        >
            <span class="icon icon-svg" aria-hidden="true">...</span>
            <span>Ver Detalhes</span>
        </a>
        
        <div class="article-icons" role="group" aria-label="Ações rápidas">
            <button 
                type="button"
                class="article-icon-button"
                aria-label="Salvar artigo para leitura posterior"
                aria-pressed="false"
                onclick="toggleSaveArticle({{ article.id }})"
                onkeydown="handleKeyDown(event, () => toggleSaveArticle({{ article.id }}))"
            >
                <span class="icon icon-svg" aria-hidden="true">...</span>
                <span class="sr-only">Salvar</span>
            </button>
            
            <button 
                type="button"
                class="article-icon-button share-article-btn"
                aria-label="Compartilhar artigo"
                data-article-id="{{ article.id }}"
                data-article-title="{{ (article.title_translated or article.title)|replace('"', '&quot;') }}"
                onclick="shareArticle({{ article.id }})"
                onkeydown="handleKeyDown(event, () => shareArticle({{ article.id }}))"
            >
                <span class="icon icon-svg" aria-hidden="true">...</span>
                <span class="sr-only">Compartilhar</span>
            </button>
        </div>
    </div>
</article>
```

---

## 🔍 Testes Recomendados

### Acessibilidade
1. **Teste com leitores de tela:**
   - NVDA (Windows)
   - JAWS (Windows)
   - VoiceOver (macOS/iOS)

2. **Teste de navegação por teclado:**
   - Tab para navegar
   - Enter/Space para ativar
   - Escape para fechar modais

3. **Teste de contraste:**
   - Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
   - Verifique todos os textos contra seus backgrounds

### Responsividade
1. **Teste em dispositivos reais:**
   - iPhone SE (375px)
   - iPhone 12/13 (390px)
   - Android pequeno (360px)
   - Tablet (768px)

2. **Teste de touch targets:**
   - Todos os elementos clicáveis devem ter mínimo 44x44px
   - Espaçamento adequado entre elementos

### Performance
1. **Teste de carregamento:**
   - Lighthouse (Chrome DevTools)
   - WebPageTest
   - Verificar First Contentful Paint (FCP)
   - Verificar Largest Contentful Paint (LCP)

---

**Próximos Passos:**
1. Implementar melhorias de acessibilidade
2. Adicionar skeleton loaders
3. Melhorar responsividade mobile
4. Testar com ferramentas de acessibilidade
5. Coletar feedback de usuários

---

**Gerado por:** MCP UI-Expert  
**Versão:** 1.0  
**Data:** 2025-01-27

