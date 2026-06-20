# Exemplos de Componentes Melhorados

Este arquivo contém exemplos práticos de componentes melhorados seguindo as recomendações da análise UI/UX.

---

## 1. Botão de Fechar Modal (Melhorado)

### ❌ Antes (Problemas)
```html
<button 
    class="absolute top-4 right-4 p-2 bg-slate-100 hover:bg-slate-200 rounded-full text-slate-500 hover:text-slate-900 transition-colors z-10"
    onclick="document.getElementById('modal-container').innerHTML=''"
>
    {{ icon('x', 'w-5 h-5') | safe }}
</button>
```

**Problemas:**
- Sem ARIA label
- Sem suporte a teclado (ESC)
- Sem feedback visual para foco
- onclick inline (não acessível)

### ✅ Depois (Melhorado)
```html
<button 
    type="button"
    aria-label="Fechar modal"
    class="absolute top-4 right-4 p-2 bg-slate-100 hover:bg-slate-200 rounded-full text-slate-500 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors z-10"
    onclick="closeModal()"
    onkeydown="if(event.key === 'Escape') closeModal()"
>
    <span class="sr-only">Fechar</span>
    {{ icon('x', 'w-5 h-5', aria-hidden='true') | safe }}
</button>

<script>
function closeModal() {
    const modal = document.getElementById('modal-container');
    if (modal) {
        modal.innerHTML = '';
        // Retornar foco para elemento que abriu o modal
        document.activeElement?.blur();
    }
}

// Fechar modal com ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('modal-container');
        if (modal && modal.innerHTML.trim() !== '') {
            closeModal();
        }
    }
});
</script>
```

**Melhorias:**
- ✅ ARIA label descritivo
- ✅ Suporte a teclado (ESC)
- ✅ Focus ring visível
- ✅ Texto para screen readers (`sr-only`)
- ✅ Função reutilizável

---

## 2. Campo de Busca (Melhorado)

### ❌ Antes
```html
<input 
    type="search" 
    name="search"
    placeholder="Buscar artigos..." 
    class="w-64 pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm transition-all"
    hx-get="/search-suggestions"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#search-results"
    hx-indicator="#search-spinner"
>
```

### ✅ Depois (Melhorado)
```html
<div class="relative">
    <label for="search-input" class="sr-only">
        Buscar artigos científicos
    </label>
    <input 
        id="search-input"
        type="search" 
        name="search"
        placeholder="Buscar artigos..." 
        aria-label="Buscar artigos científicos"
        aria-describedby="search-description"
        aria-controls="search-results"
        aria-expanded="false"
        autocomplete="off"
        class="w-full sm:w-64 pl-10 pr-10 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm transition-all"
        hx-get="/search-suggestions"
        hx-trigger="keyup changed delay:500ms, search"
        hx-target="#search-results"
        hx-indicator="#search-spinner"
        hx-swap="innerHTML"
    >
    <div class="absolute left-3 top-2.5 text-slate-400 pointer-events-none">
        {{ icon('search', 'w-4 h-4', aria-hidden='true') | safe }}
    </div>
    <div id="search-spinner" class="htmx-indicator absolute right-3 top-2.5" aria-hidden="true">
        <span class="sr-only">Buscando...</span>
        {{ icon('loader-2', 'w-4 h-4 animate-spin text-blue-600') | safe }}
    </div>
    <div id="search-description" class="sr-only">
        Digite para buscar artigos. Use as setas para navegar e Enter para selecionar.
    </div>
    <!-- Search Dropdown Results -->
    <div 
        id="search-results" 
        role="listbox"
        aria-label="Resultados da busca"
        class="absolute top-full left-0 right-0 mt-2 bg-white rounded-lg shadow-xl border border-slate-100 hidden empty:hidden z-50"
    ></div>
</div>

<script>
// Melhorar navegação por teclado nos resultados
document.addEventListener('htmx:afterSwap', (e) => {
    if (e.target.id === 'search-results') {
        const results = e.target.querySelectorAll('[role="option"]');
        if (results.length > 0) {
            results[0].focus();
            document.getElementById('search-input').setAttribute('aria-expanded', 'true');
        }
    }
});
</script>
```

**Melhorias:**
- ✅ Label acessível (visível e oculta)
- ✅ ARIA attributes completos
- ✅ Responsivo (w-full sm:w-64)
- ✅ Descrição para screen readers
- ✅ Navegação por teclado melhorada

---

## 3. Card de Artigo (Melhorado)

### ❌ Antes (Problemas)
```html
<h3 class="text-lg font-bold text-slate-900 mb-2 leading-tight group-hover:text-blue-600 transition-colors">
    <a href="/articles/{{ article.id }}" 
       hx-get="/articles/{{ article.id }}" 
       hx-target="#modal-container" 
       hx-swap="innerHTML"
       hx-push-url="true">
        {{ article.title_translated or article.title }}
    </a>
</h3>
```

### ✅ Depois (Melhorado)
```html
<article class="group bg-white rounded-xl shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 border border-slate-200 flex flex-col h-full overflow-hidden" 
         itemscope 
         itemtype="https://schema.org/ScholarlyArticle">
    <div class="p-6 flex flex-col flex-grow">
        <!-- Header: Category & Date -->
        <header class="flex justify-between items-start mb-4">
            <div class="flex flex-wrap gap-2" role="list">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100" role="listitem">
                    {{ article.category.name if article.category else 'Geral' }}
                </span>
                
                {% if article.journal_name %}
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-100 uppercase tracking-wide" role="listitem">
                    {{ icon('book', 'w-3 h-3', aria-hidden='true') | safe }}
                    <span class="sr-only">Publicado em periódico científico</span>
                    Periódico científico
                </span>
                {% endif %}
            </div>
            
            <time datetime="{{ article.publication_date.isoformat() }}" class="text-xs text-slate-400 flex items-center gap-1 whitespace-nowrap ml-2">
                {{ icon('calendar', 'w-3 h-3', aria-hidden='true') | safe }}
                <span class="sr-only">Data de publicação:</span>
                {{ article.publication_date | date_fmt }}
            </time>
        </header>

        <!-- Title -->
        <h3 class="text-lg font-bold text-slate-900 mb-2 leading-tight group-hover:text-blue-600 transition-colors">
            <a href="/articles/{{ article.id }}" 
               hx-get="/articles/{{ article.id }}" 
               hx-target="#modal-container" 
               hx-swap="innerHTML"
               hx-push-url="true"
               class="focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
               itemprop="headline">
                {{ article.title_translated or article.title }}
            </a>
        </h3>

        <!-- Authors -->
        <div class="flex items-center gap-2 text-sm text-slate-600 mb-3" itemprop="author" itemscope itemtype="https://schema.org/Person">
            <span class="text-slate-400" aria-hidden="true">
                {{ icon('users', 'w-4 h-4') | safe }}
            </span>
            <span class="truncate" itemprop="name">
                {% if article.authors %}
                    {{ article.authors|map(attribute='name')|join(', ') }}
                {% else %}
                    Autores desconhecidos
                {% endif %}
            </span>
        </div>

        <!-- Abstract Preview -->
        <p class="text-sm text-slate-500 line-clamp-3 mb-4 flex-grow" itemprop="description">
            {{ article.abstract_translated or article.abstract or 'Sem resumo disponível.' }}
        </p>

        <!-- Footer: Journal & Metrics -->
        <footer class="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span class="flex items-center gap-1 max-w-[60%] truncate" title="{{ article.journal_name or article.feed.name }}">
                {% if article.journal_name %}
                    {{ icon('book-open', 'w-3 h-3 text-purple-600', aria-hidden='true') | safe }}
                    <span class="font-medium text-purple-700" itemprop="publisher">{{ article.journal_name }}</span>
                {% else %}
                    {{ icon('rss', 'w-3 h-3 text-orange-500', aria-hidden='true') | safe }}
                    <span class="font-medium text-orange-700">Blog/Portal</span>
                {% endif %}
            </span>
            
            <div class="flex items-center gap-3" role="list">
                {% if article.pdf_file_path %}
                <span class="flex items-center gap-1 text-red-600 bg-red-50 px-1.5 py-0.5 rounded" title="PDF Disponível" role="listitem">
                    {{ icon('file-text', 'w-3 h-3', aria-hidden='true') | safe }}
                    <span class="sr-only">PDF disponível para download</span>
                    PDF
                </span>
                {% endif %}
            </div>
        </footer>
    </div>
    
    <!-- Quick Actions -->
    <nav class="px-6 py-3 bg-slate-50 border-t border-slate-100 flex gap-2 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity" aria-label="Ações rápidas">
        <button 
            class="flex-1 flex items-center justify-center gap-2 text-sm font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 px-3 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            hx-get="/articles/{{ article.id }}"
            hx-target="#modal-container"
            hx-swap="innerHTML"
            aria-label="Ver detalhes do artigo: {{ article.title_translated or article.title }}"
        >
            {{ icon('eye', 'w-4 h-4', aria-hidden='true') | safe }}
            Ver detalhes
        </button>
        {% if article.pdf_file_path %}
        <a href="/download/{{ article.id }}" 
           class="flex items-center justify-center p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
           title="Download PDF"
           download
           aria-label="Baixar PDF do artigo: {{ article.title_translated or article.title }}">
            {{ icon('download', 'w-4 h-4', aria-hidden='true') | safe }}
            <span class="sr-only">Download PDF</span>
        </a>
        {% endif %}
    </nav>
</article>
```

**Melhorias:**
- ✅ Semantic HTML (`<article>`, `<header>`, `<footer>`, `<nav>`)
- ✅ Schema.org structured data
- ✅ ARIA labels e roles
- ✅ Focus states visíveis
- ✅ Screen reader support
- ✅ Melhor navegação por teclado

---

## 4. Componente de Loading (Novo)

```html
<!-- Loading Spinner Reutilizável -->
<div class="htmx-indicator flex items-center justify-center p-8" role="status" aria-live="polite">
    <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" aria-hidden="true"></div>
        <span class="text-sm text-slate-600 font-medium">Carregando...</span>
    </div>
    <span class="sr-only">Carregando conteúdo, por favor aguarde.</span>
</div>

<!-- Skeleton Loader para Cards -->
<div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 animate-pulse">
    <div class="flex justify-between items-start mb-4">
        <div class="h-6 w-24 bg-slate-200 rounded"></div>
        <div class="h-4 w-20 bg-slate-200 rounded"></div>
    </div>
    <div class="h-6 w-full bg-slate-200 rounded mb-2"></div>
    <div class="h-6 w-3/4 bg-slate-200 rounded mb-4"></div>
    <div class="h-4 w-full bg-slate-200 rounded mb-2"></div>
    <div class="h-4 w-5/6 bg-slate-200 rounded"></div>
</div>
```

---

## 5. Componente de Erro (Novo)

```html
<!-- Toast de Erro -->
<div role="alert" aria-live="assertive" class="fixed top-4 right-4 z-50 max-w-sm">
    <div class="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg shadow-lg">
        <div class="flex items-start">
            <div class="flex-shrink-0">
                {{ icon('alert-circle', 'w-5 h-5 text-red-600', aria-hidden='true') | safe }}
            </div>
            <div class="ml-3 flex-1">
                <h3 class="text-sm font-medium text-red-800">
                    Erro ao processar requisição
                </h3>
                <p class="mt-1 text-sm text-red-700" id="error-message">
                    {{ error_message or 'Ocorreu um erro inesperado. Tente novamente.' }}
                </p>
            </div>
            <button 
                type="button"
                aria-label="Fechar notificação de erro"
                class="ml-4 flex-shrink-0 text-red-600 hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
                onclick="this.closest('[role=alert]').remove()"
            >
                {{ icon('x', 'w-5 h-5', aria-hidden='true') | safe }}
            </button>
        </div>
    </div>
</div>

<!-- Estado Vazio -->
<div class="text-center py-12" role="status">
    <div class="mx-auto w-16 h-16 text-slate-300 mb-4">
        {{ icon('inbox', 'w-16 h-16', aria-hidden='true') | safe }}
    </div>
    <h3 class="text-lg font-semibold text-slate-900 mb-2">
        Nenhum resultado encontrado
    </h3>
    <p class="text-slate-600 mb-6">
        Tente ajustar os filtros ou fazer uma nova busca.
    </p>
    <button 
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        onclick="document.getElementById('filter-form').reset(); document.getElementById('filter-form').requestSubmit();"
    >
        Limpar filtros
    </button>
</div>
```

---

## 6. Utilitários CSS para Acessibilidade

Adicionar ao `app.css` ou criar `accessibility.css`:

```css
/* Screen Reader Only */
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

/* Focus Visible (melhor que outline padrão) */
.focus-visible-ring {
    outline: 2px solid transparent;
    outline-offset: 2px;
}

.focus-visible-ring:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}

/* Skip to main content (para navegação por teclado) */
.skip-to-main {
    position: absolute;
    top: -40px;
    left: 0;
    background: #3b82f6;
    color: white;
    padding: 8px 16px;
    text-decoration: none;
    z-index: 100;
}

.skip-to-main:focus {
    top: 0;
}

/* Melhorar contraste em modo de alto contraste */
@media (prefers-contrast: high) {
    .card {
        border-width: 2px;
    }
    
    .btn {
        border-width: 2px;
    }
}

/* Reduzir animações para usuários que preferem */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## 7. Template Helper para Ícones Acessíveis

Criar helper no backend (Jinja2):

```python
# app/utils/icons.py (melhorar função existente)
def icon(name: str, classes: str = "w-5 h-5", aria_hidden: bool = True) -> str:
    """
    Gera ícone Lucide com suporte a acessibilidade.
    """
    aria_attr = 'aria-hidden="true"' if aria_hidden else ''
    return f'<i data-lucide="{name}" class="{classes}" {aria_attr}></i>'
```

---

## Resumo das Melhorias

| Componente | Melhorias Aplicadas |
|------------|---------------------|
| Botão Fechar | ARIA labels, teclado, focus ring |
| Campo Busca | Labels, ARIA, responsivo, navegação |
| Card Artigo | Semantic HTML, Schema.org, ARIA |
| Loading | Estados acessíveis, skeleton |
| Erro | Alert roles, mensagens claras |
| Utilitários | CSS para acessibilidade |

---

**Próximos Passos:**
1. Implementar esses componentes melhorados
2. Testar com leitores de tela (NVDA, JAWS, VoiceOver)
3. Validar com ferramentas de acessibilidade (axe, WAVE)
4. Testar navegação apenas por teclado
5. Verificar contraste de cores

