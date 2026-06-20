# 🚀 Guia de Início Rápido - Implementação UI/UX

Este guia fornece os passos práticos para começar a implementação imediatamente.

---

## 📋 Pré-requisitos

- Node.js e npm instalados (para Tailwind CSS)
- Acesso ao projeto BHUB
- Editor de código configurado

---

## 🎯 Passo 1: Configurar Design Tokens (30 minutos)

### 1.1. Criar arquivo de design tokens

Crie o arquivo `app/static/css/design-tokens.css`:

```css
:root {
  /* CORES PRIMÁRIAS - Paleta Oficial Teal/Verde-água */
  --color-primary-50: #e6f7f5;
  --color-primary-100: #b3e8e2;
  --color-primary-200: #80d9cf;
  --color-primary-300: #4dcabc;
  --color-primary-400: #3fb5a3;    /* PRIMÁRIA */
  --color-primary-500: #10908d;
  --color-primary-600: #0d7a78;
  --color-primary-700: #135a5a;
  --color-primary-800: #0f4847;
  --color-primary-900: #0b3536;    /* MODO ESCURO */

  /* Verde Pastel */
  --color-accent-light: #daedd6;
  --color-accent-light-hover: #c8e4c0;

  /* SEMÂNTICAS - Modo Claro */
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #daedd6;
  --color-text-primary: #0b3536;
  --color-text-secondary: #135a5a;
  --color-border-light: #e5e5e5;
}

/* Modo Escuro */
[data-theme="dark"],
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg-primary: #0b3536;
    --color-bg-secondary: #135a5a;
    --color-text-primary: #daedd6;
    --color-text-secondary: #b3e8e2;
    --color-border-light: #135a5a;
  }
}
```

### 1.2. Carregar no base.html

Adicione no `<head>` do `app/templates/base.html`:

```html
<link rel="stylesheet" href="{{ url_for('static', path='css/design-tokens.css') }}">
```

---

## 🎯 Passo 2: Configurar Tailwind CSS (1 hora)

### 2.1. Instalar dependências

```bash
cd bhub-backend-python
npm init -y  # Se não tiver package.json
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 2.2. Configurar tailwind.config.js

Substitua o conteúdo por:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e6f7f5',
          100: '#b3e8e2',
          200: '#80d9cf',
          300: '#4dcabc',
          400: '#3fb5a3',  // Cor principal da paleta
          500: '#10908d',
          600: '#0d7a78',
          700: '#135a5a',
          800: '#0f4847',
          900: '#0b3536',  // Modo escuro
        },
        accent: {
          light: '#daedd6',
          'light-hover': '#c8e4c0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### 2.3. Criar input.css

Crie `app/static/css/input.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Utilitários customizados */
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

### 2.4. Adicionar scripts ao package.json

```json
{
  "scripts": {
    "build-css": "tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --minify",
    "watch-css": "tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --watch"
  }
}
```

### 2.5. Compilar CSS

```bash
npm run build-css
```

### 2.6. Atualizar base.html

Substitua o CDN do Tailwind por:

```html
<!-- Em desenvolvimento: usar CDN ou watch mode -->
<!-- <script src="https://cdn.tailwindcss.com"></script> -->

<!-- Em produção: usar CSS compilado -->
<link rel="stylesheet" href="{{ url_for('static', path='css/output.css') }}">
```

---

## 🎯 Passo 3: Migrar Primeira Página (1 hora)

### 3.1. Migrar login.html

Substitua as classes do `app.css` por classes Tailwind:

**Antes:**
```html
<section class="panel">
  <div class="panel-body">
    <h1>Entrar</h1>
    <div class="muted">Use seu email...</div>
  </div>
</section>
```

**Depois:**
```html
<section class="bg-white rounded-xl shadow-lg border border-primary-200 p-8 max-w-md mx-auto">
  <div>
    <h1 class="text-2xl font-bold text-primary-900 mb-2">Entrar</h1>
    <div class="text-primary-700 mb-6">Use seu email...</div>
    
    <form method="post" action="/login">
      <div class="mb-4">
        <label for="username" class="block text-sm font-medium text-primary-700 mb-2">
          Email
        </label>
        <input 
          id="username" 
          name="username" 
          type="email" 
          required 
          autocomplete="email"
          class="w-full px-4 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-400 focus:border-transparent"
        />
      </div>
      
      <div class="mb-6">
        <label for="password" class="block text-sm font-medium text-primary-700 mb-2">
          Senha
        </label>
        <input 
          id="password" 
          name="password" 
          type="password" 
          required 
          autocomplete="current-password"
          class="w-full px-4 py-2 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-400 focus:border-transparent"
        />
      </div>
      
      <div class="flex gap-4">
        <button 
          type="submit" 
          class="px-6 py-2 bg-primary-400 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors"
        >
          Entrar
        </button>
        <a 
          href="/" 
          class="px-6 py-2 border border-primary-300 text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-colors"
        >
          Voltar
        </a>
      </div>
    </form>
  </div>
</section>
```

---

## 🎯 Passo 4: Adicionar Acessibilidade Básica (30 minutos)

### 4.1. Criar accessibility.css

Crie `app/static/css/accessibility.css`:

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

/* Focus Visible */
*:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
}

/* Skip to main content */
.skip-to-main {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-primary-400);
  color: white;
  padding: 8px 16px;
  text-decoration: none;
  z-index: 100;
}

.skip-to-main:focus {
  top: 0;
}

/* Reduced motion */
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

### 4.2. Adicionar ao base.html

```html
<link rel="stylesheet" href="{{ url_for('static', path='css/accessibility.css') }}">
```

### 4.3. Melhorar botão de fechar modal

Adicione no `app/static/js/app.js`:

```javascript
// Fechar modal com ESC
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('modal-container');
    if (modal && modal.innerHTML.trim() !== '') {
      modal.innerHTML = '';
    }
  }
});
```

---

## 🎯 Passo 5: Testar e Validar (30 minutos)

### 5.1. Testar visualmente

- [ ] Abrir login.html e verificar aparência
- [ ] Verificar se cores da paleta estão aplicadas
- [ ] Testar responsividade (redimensionar janela)
- [ ] Verificar se não há quebras visuais

### 5.2. Validar acessibilidade

- [ ] Testar navegação por teclado (Tab, Enter, Esc)
- [ ] Verificar contraste de cores (usar WebAIM)
- [ ] Testar com screen reader (opcional)

### 5.3. Verificar performance

- [ ] Verificar tamanho do CSS compilado
- [ ] Testar tempo de carregamento
- [ ] Verificar se não há erros no console

---

## ✅ Checklist de Validação

Após completar os passos acima, verifique:

- [ ] Design tokens criados e carregados
- [ ] Tailwind configurado com paleta oficial
- [ ] CSS compilado funcionando
- [ ] login.html migrado e funcional
- [ ] Acessibilidade básica implementada
- [ ] Sem erros no console
- [ ] Visual consistente

---

## 🚀 Próximos Passos

Após completar este guia:

1. **Continuar com Fase 1.2**: Adicionar ARIA labels em todos os componentes
2. **Migrar outras páginas**: home.html, article_detail.html, etc.
3. **Implementar componentes de feedback**: loading, error, empty
4. **Seguir o plano completo**: `PLANO_IMPLEMENTACAO_UI_UX.md`

---

## 🆘 Troubleshooting

### CSS não está sendo aplicado
- Verificar se `output.css` foi gerado
- Verificar caminho no `base.html`
- Limpar cache do navegador

### Tailwind não compila
- Verificar se `content` paths estão corretos
- Verificar se `input.css` existe
- Executar `npm run build-css` novamente

### Cores não aparecem
- Verificar se `tailwind.config.js` tem as cores
- Verificar se classes estão usando `primary-400`, etc.
- Recompilar CSS após mudanças no config

---

## 📚 Recursos

- [Paleta de Cores Completa](./PALETA_CORES.md)
- [Plano Completo de Implementação](./PLANO_IMPLEMENTACAO_UI_UX.md)
- [Análise UI/UX Detalhada](./UI_UX_ANALYSIS.md)
- [Exemplos de Componentes](./UI_UX_COMPONENT_EXAMPLES.md)

---

**Última atualização:** 2025-01-19  
**Tempo estimado total:** 3-4 horas para completar este guia

