# Correções para Busca Avançada - Aplicar Imediatamente

## 🔧 Correções Necessárias no `articles.html`

### 1. Adicionar Trigger Centralizado no Formulário

**Localização:** Linha 37-43

**ANTES:**
```html
<form id="advanced-search-form" 
      hx-get="/articles" 
      hx-target="#search-results" 
      hx-indicator="#search-loading"
      hx-push-url="true"
      hx-swap="innerHTML"
      class="filters-form">
```

**DEPOIS:**
```html
<form id="advanced-search-form" 
      hx-get="/articles" 
      hx-target="#search-results" 
      hx-indicator="#search-loading"
      hx-push-url="true"
      hx-swap="innerHTML"
      hx-trigger="submit, change delay:500ms from:#advanced-search-form input[type='checkbox'], change delay:300ms from:#advanced-search-form select, change delay:800ms from:#search-input-advanced"
      class="filters-form">
```

---

### 2. Remover Triggers Individuais dos Radio Buttons

**Localização:** Linhas 50-57 e 61-68

**ANTES:**
```html
<input type="radio" name="search_type" value="text" 
       hx-get="/articles"
       hx-target="#search-results"
       hx-include="#advanced-search-form"
       hx-trigger="change"
       hx-swap="innerHTML"
       hx-push-url="true"
       hx-indicator="#search-loading">
```

**DEPOIS:**
```html
<input type="radio" name="search_type" value="text" 
       {% if (filters.search_type if filters else 'text') == 'text' %}checked{% endif %} 
       class="sr-only">
```

**Aplicar a mesma correção para o radio button "semantic" (linhas 61-68)**

---

### 3. Remover Trigger Individual do Input de Busca

**Localização:** Linhas 81-96

**ANTES:**
```html
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
    hx-trigger="keyup changed delay:500ms, search"
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

**DEPOIS:**
```html
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
```

---

### 4. Remover Triggers Individuais dos Checkboxes de Categorias

**Localização:** Linhas 113-126

**ANTES:**
```html
<input 
    type="checkbox" 
    name="category_id" 
    value="{{ cat.id }}" 
    class="filter-checkbox"
    {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-trigger="change"
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

**DEPOIS:**
```html
<input 
    type="checkbox" 
    name="category_id" 
    value="{{ cat.id }}" 
    class="filter-checkbox"
    {% if filters and filters.category_ids and cat.id in filters.category_ids %}checked{% endif %}
>
```

---

### 5. Remover Triggers Individuais do Select de Source Type

**Localização:** Linhas 137-148

**ANTES:**
```html
<select 
    id="source-category-advanced"
    name="source_category" 
    class="filter-select"
    hx-get="/articles"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-trigger="change"
    hx-swap="innerHTML"
    hx-push-url="true"
    hx-indicator="#search-loading"
>
```

**DEPOIS:**
```html
<select 
    id="source-category-advanced"
    name="source_category" 
    class="filter-select"
>
```

---

### 6. Remover Triggers Individuais de Todos os Outros Campos

Aplicar a mesma correção (remover todos os atributos `hx-*`) para:

- **Feed Filter** (linhas ~159-170)
- **Date Inputs** (linhas ~185-215)
- **Checkboxes Adicionais** (highlighted, has_pdf, is_open_access) (linhas ~224-276)
- **Sort Selects** (linhas ~284-315)

**Padrão a seguir:**
- Remover: `hx-get`, `hx-target`, `hx-include`, `hx-trigger`, `hx-swap`, `hx-push-url`, `hx-indicator`
- Manter: `name`, `value`, `class`, `id`, `type`, `checked`, `selected`

---

### 7. Adicionar JavaScript para Paginação

**Localização:** Antes do `</script>` final (linha ~895)

**ADICIONAR:**
```javascript
// Função para navegação de páginas mantendo filtros
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
                // Para checkboxes múltiplos, adicionar cada um
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
```

---

### 8. Atualizar Botões de Paginação

**Localização:** `partials/articles/list.html` (linhas 21-31, 60-72, 86-98)

**ANTES:**
```html
<button 
    hx-get="/articles?page={{ page - 1 }}"
    hx-target="#search-results"
    hx-include="#advanced-search-form"
    hx-swap="innerHTML"
    hx-push-url="true"
    ...
>
```

**DEPOIS:**
```html
<button 
    type="button"
    onclick="goToPage({{ page - 1 }})"
    ...
>
```

**Aplicar para:**
- Botão "Anterior" (linha ~21)
- Botões de número de página (linha ~60)
- Botão "Próxima" (linha ~86)

---

## 📝 Resumo das Mudanças

1. ✅ Adicionar `hx-trigger` centralizado no formulário
2. ✅ Remover todos os `hx-*` dos radio buttons
3. ✅ Remover `hx-*` do input de busca (usar botão submit)
4. ✅ Remover todos os `hx-*` dos checkboxes
5. ✅ Remover todos os `hx-*` dos selects
6. ✅ Remover todos os `hx-*` dos date inputs
7. ✅ Adicionar função JavaScript `goToPage()`
8. ✅ Atualizar botões de paginação para usar `goToPage()`

---

## 🧪 Como Testar

1. **Teste de Checkbox:**
   - Marcar uma categoria → deve filtrar após 500ms
   - Desmarcar → deve remover filtro

2. **Teste de Busca:**
   - Digitar no campo → deve buscar após 800ms
   - Clicar no botão de busca → deve buscar imediatamente
   - Pressionar Enter → deve buscar imediatamente

3. **Teste de Paginação:**
   - Clicar em "Próxima" → deve manter todos os filtros
   - Clicar em número de página → deve manter todos os filtros

4. **Teste de Combinação:**
   - Aplicar múltiplos filtros → todos devem funcionar
   - Navegar entre páginas → filtros devem ser mantidos

---

## ⚠️ Importante

- **NÃO** adicione triggers individuais de volta
- **NÃO** use `hx-include` em elementos individuais
- **SIM** use apenas o trigger centralizado do formulário
- **SIM** use a função `goToPage()` para paginação

---

**Próximo Passo:** Aplicar todas as correções acima e testar!

