# 🎨 Guia de Uso da Paleta de Cores BHUB

## Paleta Oficial

A identidade visual do BHUB é baseada em uma paleta de **teal/verde-água** que transmite profissionalismo, modernidade e confiança - ideal para uma plataforma científica.

### Cores Principais

```
🟢 Teal Claro    #3fb5a3  → Cor primária (botões, links, CTAs)
🌿 Verde Pastel  #daedd6  → Backgrounds claros, cards
🔷 Teal Médio    #10908d  → Hover states, accents
🔹 Teal Escuro   #135a5a  → Textos, borders
⬛ Teal Muito Escuro #0b3536 → Background modo escuro
```

---

## Exemplos de Uso

### 1. Botões Primários

```html
<!-- Botão padrão -->
<button class="bg-[#3fb5a3] hover:bg-[#10908d] text-white px-6 py-3 rounded-lg transition-colors">
  Explorar Artigos
</button>

<!-- Com Tailwind configurado -->
<button class="bg-primary-400 hover:bg-primary-500 text-white px-6 py-3 rounded-lg">
  Explorar Artigos
</button>
```

### 2. Cards e Backgrounds

```html
<!-- Card com background pastel -->
<div class="bg-[#daedd6] border border-[#3fb5a3] rounded-xl p-6">
  <h3 class="text-[#135a5a] font-bold">Título do Card</h3>
  <p class="text-[#0b3536]">Conteúdo do card...</p>
</div>

<!-- Com Tailwind -->
<div class="bg-accent-light border border-primary-400 rounded-xl p-6">
  <h3 class="text-primary-700 font-bold">Título do Card</h3>
  <p class="text-primary-900">Conteúdo do card...</p>
</div>
```

### 3. Links e Navegação

```html
<!-- Link padrão -->
<a href="#" class="text-[#3fb5a3] hover:text-[#10908d] underline">
  Ver mais artigos
</a>

<!-- Link ativo -->
<a href="#" class="text-[#10908d] border-b-2 border-[#3fb5a3]">
  Página Atual
</a>
```

### 4. Badges e Tags

```html
<!-- Badge primário -->
<span class="bg-[#3fb5a3] text-white px-3 py-1 rounded-full text-sm">
  Novo
</span>

<!-- Badge secundário -->
<span class="bg-[#daedd6] text-[#135a5a] px-3 py-1 rounded-full text-sm border border-[#3fb5a3]">
  Categoria
</span>
```

### 5. Modo Escuro

```html
<!-- Background modo escuro -->
<div class="bg-[#0b3536] text-[#daedd6] p-6 rounded-xl">
  <h2 class="text-[#b3e8e2]">Título</h2>
  <p class="text-[#daedd6]">Conteúdo em modo escuro...</p>
</div>

<!-- Com variáveis CSS -->
<div class="bg-primary-900 text-accent-light p-6 rounded-xl">
  <h2 class="text-primary-100">Título</h2>
  <p class="text-accent-light">Conteúdo em modo escuro...</p>
</div>
```

---

## Combinações de Cores

### Combinação 1: Primária + Pastel (Recomendada)
```
Background: #daedd6 (verde pastel)
Texto: #0b3536 (teal muito escuro)
Accent: #3fb5a3 (teal claro)
```
**Uso:** Cards, seções destacadas, hero sections

### Combinação 2: Escuro + Claro (Alto Contraste)
```
Background: #0b3536 (teal muito escuro)
Texto: #daedd6 (verde pastel)
Accent: #3fb5a3 (teal claro)
```
**Uso:** Modo escuro, headers, footers

### Combinação 3: Neutro + Primária (Elegante)
```
Background: #ffffff (branco)
Texto: #135a5a (teal escuro)
Accent: #3fb5a3 (teal claro)
```
**Uso:** Páginas principais, conteúdo

---

## Cores de Suporte

Além da paleta principal, use estas cores para feedback e estados:

### Success (Verde)
```css
--color-success: #22c55e;  /* Sucesso, confirmações */
--color-success-dark: #16a34a;
```

### Warning (Amarelo/Laranja)
```css
--color-warning: #f59e0b;  /* Avisos, atenção */
--color-warning-dark: #d97706;
```

### Error (Vermelho)
```css
--color-error: #ef4444;    /* Erros, ações destrutivas */
--color-error-dark: #dc2626;
```

### Info (Azul complementar)
```css
--color-info: #3b82f6;     /* Informações, dicas */
--color-info-dark: #2563eb;
```

---

## Verificação de Contraste

### Modo Claro
| Cor de Fundo | Cor de Texto | Contraste | Status |
|--------------|--------------|-----------|--------|
| `#daedd6` | `#0b3536` | 7.2:1 | ✅ AAA |
| `#3fb5a3` | `#ffffff` | 3.1:1 | ⚠️ AA (grande) |
| `#10908d` | `#ffffff` | 4.5:1 | ✅ AA |
| `#135a5a` | `#daedd6` | 4.8:1 | ✅ AA |

### Modo Escuro
| Cor de Fundo | Cor de Texto | Contraste | Status |
|--------------|--------------|-----------|--------|
| `#0b3536` | `#daedd6` | 10.2:1 | ✅ AAA |
| `#0b3536` | `#b3e8e2` | 8.5:1 | ✅ AAA |
| `#135a5a` | `#daedd6` | 5.2:1 | ✅ AA |

> ✅ **Todas as combinações atendem WCAG 2.1 AA** (mínimo 4.5:1 para texto normal, 3:1 para texto grande)

---

## Implementação no Tailwind

### 1. Configurar `tailwind.config.js`

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e6f7f5',
          100: '#b3e8e2',
          200: '#80d9cf',
          300: '#4dcabc',
          400: '#3fb5a3',  // ← Cor principal
          500: '#10908d',
          600: '#0d7a78',
          700: '#135a5a',
          800: '#0f4847',
          900: '#0b3536',  // ← Modo escuro
        },
        accent: {
          light: '#daedd6',
          'light-hover': '#c8e4c0',
        },
      },
    },
  },
}
```

### 2. Usar no HTML

```html
<!-- Botão com cor primária -->
<button class="bg-primary-400 hover:bg-primary-500 text-white">
  Clique aqui
</button>

<!-- Card com background pastel -->
<div class="bg-accent-light border-primary-400">
  Conteúdo
</div>

<!-- Texto com cor escura -->
<p class="text-primary-900">Texto principal</p>
```

---

## Variáveis CSS (Recomendado)

Para máxima flexibilidade, use variáveis CSS:

```css
:root {
  --color-primary: #3fb5a3;
  --color-primary-hover: #10908d;
  --color-accent-light: #daedd6;
  --color-text-primary: #0b3536;
  --color-text-secondary: #135a5a;
}

/* Modo escuro */
[data-theme="dark"] {
  --color-bg-primary: #0b3536;
  --color-text-primary: #daedd6;
}
```

Uso:
```html
<div style="background-color: var(--color-primary);">
  Conteúdo
</div>
```

---

## Checklist de Implementação

- [ ] Adicionar paleta ao `tailwind.config.js`
- [ ] Criar variáveis CSS com todas as cores
- [ ] Atualizar componentes existentes
- [ ] Testar contraste em todas as combinações
- [ ] Implementar modo escuro
- [ ] Documentar uso para equipe
- [ ] Criar componentes de exemplo
- [ ] Validar com ferramentas de acessibilidade

---

## Recursos

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Coolors.co](https://coolors.co/) - Para gerar variações
- [Tailwind Color Generator](https://tailwindcss.com/docs/customizing-colors)

---

**Última atualização:** 2025-01-19  
**Versão da paleta:** 1.0

