# Problemas na Busca Avançada - Análise MCP UI-Expert
## Diagnóstico e Soluções

**Data:** 2025-01-27  
**Página:** `/articles` (Busca Avançada)  
**Framework:** HTML/Tailwind CSS + HTMX

---

## 🔴 Problemas Críticos Identificados

### 1. **Múltiplos Triggers HTMX Conflitantes**

**Problema:** Cada elemento do formulário tem seu próprio trigger HTMX, causando múltiplas requisições e conflitos.

**Código problemático:**
```html
<!-- Cada checkbox tem seu próprio trigger -->
<input 
    type="checkbox" 
    name="category_id" 
    value="{{ cat.id }}"
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-trigger="change"  <!-- ⚠️ Trigger individual -->
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

**Impacto:**
- Múltiplas requisições simultâneas
- Conflitos de estado
- Performance ruim
- Resultados inconsistentes

**Solução:**
Remover triggers individuais e usar apenas o submit do formulário ou um trigger centralizado:

```html
<!-- ✅ CORRETO: Sem triggers individuais -->
<input 
    type="checkbox" 
    name="category_id" 
    value="{{ cat.id }}"
    class="filter-checkbox"
    {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
    <!-- Remover todos os atributos hx-* -->
>
```

E adicionar um trigger centralizado no formulário:

```html
<form id="advanced-search-form" 
      hx-get="/articles" 
      hx-target="#search-results" 
      hx-indicator="#search-loading"
      hx-push-url="true"
      hx-swap="innerHTML"
      hx-trigger="change delay:500ms from:#advanced-search-form input, change delay:500ms from:#advanced-search-form select, submit">
    <!-- Campos do formulário sem triggers individuais -->
</form>
```

---

### 2. **Checkboxes Não Enviando Valores Quando Desmarcados**

**Problema:** Checkboxes HTML não enviam valores quando desmarcados, então o backend não sabe quando um filtro foi removido.

**Código problemático:**
```html
<input 
    type="checkbox" 
    name="category_id" 
    value="{{ cat.id }}"
    {% if filters and filters.category_id and cat.id in filters.category_id %}checked{% endif %}
>
```

**Impacto:**
- Filtros não podem ser removidos
- Estado inconsistente entre frontend e backend
- Usuário precisa limpar todos os filtros para remover um

**Solução:**
Usar JavaScript para gerenciar o estado ou usar hidden inputs:

```html
<!-- ✅ SOLUÇÃO 1: Hidden inputs para rastrear estado -->
{% for cat in categories %}
<label class="filter-option-item">
    <input 
        type="checkbox" 
        name="category_id" 
        value="{{ cat.id }}"
        class="filter-checkbox"
        {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
        onchange="updateCategoryFilter(this)"
    >
    <span class="filter-option-text">{{ cat.name }}</span>
    <span class="filter-badge">{{ cat.article_count }}</span>
</label>
{% endfor %}

<script>
function updateCategoryFilter(checkbox) {
    // Quando desmarcado, enviar requisição sem esse category_id
    const form = document.getElementById('advanced-search-form');
    if (!checkbox.checked) {
        // Remover o valor do formulário antes de enviar
        const formData = new FormData(form);
        const categoryIds = formData.getAll('category_id');
        const index = categoryIds.indexOf(checkbox.value);
        if (index > -1) {
            categoryIds.splice(index, 1);
        }
        // Atualizar URL sem esse category_id
        const url = new URL('/articles', window.location.origin);
        categoryIds.forEach(id => url.searchParams.append('category_id', id));
        // Enviar outros parâmetros do formulário
        // ... (código completo abaixo)
    }
    // Trigger HTMX
    htmx.trigger(form, 'submit');
}
</script>
```

**Solução mais simples (recomendada):**
Usar apenas o submit do formulário e deixar o backend lidar com os valores:

```html
<!-- ✅ SOLUÇÃO 2: Deixar HTMX gerenciar automaticamente -->
<form id="advanced-search-form" 
      hx-get="/articles" 
      hx-target="#search-results" 
      hx-indicator="#search-loading"
      hx-push-url="true"
      hx-swap="innerHTML"
      hx-trigger="change delay:500ms from:#advanced-search-form, submit">
    
    <!-- Checkboxes sem triggers individuais -->
    {% for cat in categories %}
    <label class="filter-option-item">
        <input 
            type="checkbox" 
            name="category_id" 
            value="{{ cat.id }}"
            class="filter-checkbox"
            {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
        >
        <span class="filter-option-text">{{ cat.name }}</span>
        <span class="filter-badge">{{ cat.article_count }}</span>
    </label>
    {% endfor %}
</form>
```

O backend já está preparado para receber `category_id` como lista, então apenas os checkboxes marcados serão enviados.

---

### 3. **Problema com hx-include e Múltiplos Formulários**

**Problema:** O `hx-include` pode não estar funcionando corretamente quando há múltiplos elementos com triggers.

**Código problemático:**
```html
<!-- Botões de paginação usando hx-include -->
<button 
    hx-get="/articles?page={{ page + 1 }}"
    hx-target="#search-results"
    hx-include="#advanced-search-form"  <!-- ⚠️ Pode não funcionar -->
    hx-swap="innerHTML"
>
```

**Solução:**
Usar `hx-vals` ou incluir os valores diretamente na URL:

```html
<!-- ✅ SOLUÇÃO: Incluir valores do formulário na URL -->
<button 
    type="button"
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-vals='{"page": {{ page + 1 }}}'
    hx-swap="innerHTML"
    hx-push-url="true"
    class="..."
>
    Próxima
</button>
```

Ou melhor ainda, usar JavaScript para construir a URL:

```html
<button 
    type="button"
    onclick="goToPage({{ page + 1 }})"
    class="..."
>
    Próxima
</button>

<script>
function goToPage(page) {
    const form = document.getElementById('advanced-search-form');
    const formData = new FormData(form);
    formData.set('page', page);
    
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
        if (value) {
            if (key === 'category_id') {
                // Para múltiplos valores do mesmo nome
                params.append(key, value);
            } else {
                params.set(key, value);
            }
        }
    }
    
    htmx.ajax('GET', `/articles?${params.toString()}`, {
        target: '#search-results',
        swap: 'innerHTML',
        pushUrl: true
    });
}
</script>
```

---

### 4. **Input de Busca com Trigger Muito Sensível**

**Problema:** O input de busca tem `hx-trigger="keyup changed delay:500ms"`, o que pode causar muitas requisições.

**Código problemático:**
```html
<input 
    type="text" 
    name="search"
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-trigger="keyup changed delay:500ms, search"  <!-- ⚠️ Muito sensível -->
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

**Solução:**
Aumentar o delay e usar `search` event:

```html
<!-- ✅ CORRETO: Delay maior e evento search -->
<input 
    type="text" 
    id="search-input-advanced"
    name="search" 
    value="{% if filters and filters.search %}{{ filters.search }}{% endif %}"
    placeholder="Digite palavras-chave..." 
    class="filter-input"
    autocomplete="off"
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-trigger="keyup changed delay:800ms, search"  <!-- ✅ Delay maior -->
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

Ou melhor, usar apenas o botão de busca:

```html
<!-- ✅ MELHOR: Busca apenas ao clicar no botão ou pressionar Enter -->
<input 
    type="text" 
    id="search-input-advanced"
    name="search" 
    value="{% if filters and filters.search %}{{ filters.search }}{% endif %}"
    placeholder="Digite palavras-chave..." 
    class="filter-input"
    autocomplete="off"
    onkeydown="if(event.key === 'Enter') { document.getElementById('advanced-search-form').requestSubmit(); }"
>
<button 
    type="submit"
    class="filter-search-button"
    aria-label="Buscar"
>
    {{ icon('search', 'w-5 h-5', aria_hidden=True) | safe }}
</button>
```

---

### 5. **Radio Buttons com Triggers Individuais**

**Problema:** Os radio buttons têm triggers HTMX individuais, causando requisições duplicadas.

**Código problemático:**
```html
<label class="filter-radio-item">
    <input 
        type="radio" 
        name="search_type" 
        value="text"
        hx-get="/articles"  <!-- ⚠️ Trigger individual -->
        hx-target="#search-results"
        hx-include="#advanced-search-form"
        hx-trigger="change"
        hx-swap="innerHTML"
        hx-push-url="true"
        hx-indicator="#search-loading"
    >
    <span>Texto</span>
</label>
```

**Solução:**
Remover triggers individuais e usar o trigger do formulário:

```html
<!-- ✅ CORRETO: Sem triggers individuais -->
<label class="filter-radio-item">
    <input 
        type="radio" 
        name="search_type" 
        value="text"
        {% if (filters.search_type if filters else 'text') == 'text' %}checked{% endif %}
        class="sr-only"
    >
    <span class="filter-option-text">Texto</span>
</label>
```

---

## 🔧 Solução Completa Recomendada

### Formulário Refatorado

```html
<form id="advanced-search-form" 
      hx-get="/articles" 
      hx-target="#search-results" 
      hx-indicator="#search-loading"
      hx-push-url="true"
      hx-swap="innerHTML"
      hx-trigger="submit, change delay:500ms from:#advanced-search-form input[type='checkbox'], change delay:300ms from:#advanced-search-form select, change delay:800ms from:#search-input-advanced">
    
    <!-- Search Type (sem triggers individuais) -->
    <section class="filter-section">
        <label class="filter-label">Tipo de Busca</label>
        <div class="filter-options filter-radio-group">
            <label class="filter-option-item filter-radio-item {% if (filters.search_type if filters else 'text') == 'text' %}filter-radio-item-active{% endif %}">
                <input 
                    type="radio" 
                    name="search_type" 
                    value="text" 
                    {% if (filters.search_type if filters else 'text') == 'text' %}checked{% endif %}
                    class="sr-only"
                >
                <span class="filter-option-text">Texto</span>
            </label>
            <label class="filter-option-item filter-radio-item {% if (filters.search_type if filters else 'text') == 'semantic' %}filter-radio-item-active{% endif %}">
                <input 
                    type="radio" 
                    name="search_type" 
                    value="semantic" 
                    {% if (filters.search_type if filters else 'text') == 'semantic' %}checked{% endif %}
                    class="sr-only"
                >
                <span class="filter-option-text">Semântica</span>
            </label>
        </div>
    </section>

    <!-- Search Input (com botão de submit) -->
    <section class="filter-section">
        <label for="search-input-advanced" class="filter-label">Busca</label>
        <div class="relative">
            <input 
                type="text" 
                id="search-input-advanced"
                name="search" 
                value="{% if filters and filters.search %}{{ filters.search }}{% endif %}"
                placeholder="Digite palavras-chave..." 
                class="filter-input"
                autocomplete="off"
                onkeydown="if(event.key === 'Enter') { event.preventDefault(); document.getElementById('advanced-search-form').requestSubmit(); }"
            >
            <button 
                type="submit"
                class="filter-search-button"
                aria-label="Buscar"
            >
                {{ icon('search', 'w-5 h-5', aria_hidden=True) | safe }}
            </button>
        </div>
    </section>

    <!-- Categories (sem triggers individuais) -->
    <section class="filter-section">
        <label class="filter-label">Categorias</label>
        <div class="filter-options filter-categories-list">
            {% for cat in categories %}
            <label class="filter-option-item">
                <input 
                    type="checkbox" 
                    name="category_id" 
                    value="{{ cat.id }}" 
                    class="filter-checkbox"
                    {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
                >
                <span class="filter-option-text flex-grow truncate">{{ cat.name }}</span>
                <span class="filter-badge">{{ cat.article_count }}</span>
            </label>
            {% endfor %}
        </div>
    </section>

    <!-- Outros campos seguem o mesmo padrão: sem triggers individuais -->
    
</form>
```

### JavaScript para Paginação

```javascript
// Adicionar ao final do arquivo articles.html
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Função para ir para uma página específica
    window.goToPage = function(page) {
        const form = document.getElementById('advanced-search-form');
        if (!form) return;
        
        const formData = new FormData(form);
        formData.set('page', page);
        
        // Construir URL com todos os parâmetros
        const params = new URLSearchParams();
        
        // Adicionar todos os campos do formulário
        for (const [key, value] of formData.entries()) {
            if (value && value !== '') {
                if (key === 'category_id') {
                    // Para checkboxes múltiplos
                    params.append(key, value);
                } else {
                    params.set(key, value);
                }
            }
        }
        
        // Fazer requisição HTMX
        htmx.ajax('GET', `/articles?${params.toString()}`, {
            target: '#search-results',
            swap: 'innerHTML',
            pushUrl: true,
            indicator: '#search-loading'
        });
    };
    
    // Atualizar hint do tipo de busca
    const searchTypeInputs = document.querySelectorAll('input[name="search_type"]');
    const searchTypeHint = document.getElementById('search-type-hint');
    
    searchTypeInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value === 'semantic') {
                searchTypeHint.textContent = 'Busca por significado e contexto (usando IA)';
            } else {
                searchTypeHint.textContent = 'Busca por palavras-chave exatas';
            }
        });
    });
    
    // Debug: Log form data (apenas em desenvolvimento)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        document.body.addEventListener('htmx:beforeRequest', function(event) {
            if (event.detail.path && event.detail.path.includes('/articles')) {
                const form = document.getElementById('advanced-search-form');
                if (form) {
                    const formData = new FormData(form);
                    console.log('Enviando filtros:', Object.fromEntries(formData.entries()));
                }
            }
        });
    }
});
</script>
```

### Atualizar Paginação

```html
<!-- Em partials/articles/list.html -->
<button 
    type="button"
    onclick="goToPage({{ page + 1 }})"
    class="flex items-center gap-1 px-3 sm:px-4 py-2 sm:py-2.5 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 hover:text-primary-600 hover:border-primary-300 transition-all focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 min-h-[44px] text-sm sm:text-base"
    aria-label="Ir para próxima página"
>
    <span class="hidden sm:inline">Próxima</span>
    {{ icon('chevron-right', 'w-4 h-4', aria_hidden=True) | safe }}
</button>
```

---

## 📋 Checklist de Correções

- [ ] Remover todos os atributos `hx-*` individuais dos checkboxes
- [ ] Remover todos os atributos `hx-*` individuais dos radio buttons
- [ ] Remover todos os atributos `hx-*` individuais dos selects
- [ ] Adicionar trigger centralizado no formulário
- [ ] Atualizar input de busca para usar botão de submit
- [ ] Implementar função JavaScript `goToPage()` para paginação
- [ ] Atualizar botões de paginação para usar `goToPage()`
- [ ] Testar todos os filtros individualmente
- [ ] Testar combinação de múltiplos filtros
- [ ] Testar paginação com filtros ativos
- [ ] Verificar se URL está sendo atualizada corretamente
- [ ] Verificar se estado dos filtros é preservado ao navegar

---

## 🧪 Testes Recomendados

1. **Teste de Checkboxes:**
   - Marcar uma categoria → deve filtrar
   - Desmarcar uma categoria → deve remover filtro
   - Marcar múltiplas categorias → deve filtrar por todas

2. **Teste de Busca:**
   - Digitar no campo de busca → deve buscar após delay
   - Clicar no botão de busca → deve buscar imediatamente
   - Pressionar Enter → deve buscar imediatamente

3. **Teste de Paginação:**
   - Ir para próxima página → deve manter filtros
   - Voltar para página anterior → deve manter filtros
   - Ir para página específica → deve manter filtros

4. **Teste de Combinação:**
   - Busca + Categoria + Data → deve aplicar todos
   - Remover um filtro → deve manter outros
   - Limpar todos → deve mostrar todos os artigos

---

## 🐛 Debug

Adicione este código para debugar em desenvolvimento:

```javascript
// Debug HTMX requests
document.body.addEventListener('htmx:beforeRequest', function(event) {
    console.log('HTMX Request:', {
        path: event.detail.path,
        method: event.detail.verb,
        headers: event.detail.headers,
        parameters: event.detail.parameters
    });
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    console.log('HTMX Response:', {
        status: event.detail.xhr.status,
        responseText: event.detail.xhr.responseText.substring(0, 200)
    });
});
```

---

**Próximos Passos:**
1. Implementar as correções acima
2. Testar cada funcionalidade individualmente
3. Verificar se todos os filtros estão funcionando
4. Testar em diferentes navegadores
5. Verificar performance (número de requisições)

---

**Gerado por:** MCP UI-Expert  
**Versão:** 1.0  
**Data:** 2025-01-27

