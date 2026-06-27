# 🎨 Guia da Paleta de Cores BHUB — v3 (quente borgonha/sage)

> **Fonte da verdade:** os tokens vivem no código, não neste documento.
> Valores em [`app/static/css/design-tokens.css`](../../bhub-backend-python/app/static/css/design-tokens.css)
> e nas escalas do [`tailwind.config.js`](../../bhub-backend-python/tailwind.config.js).
> Este guia explica **como usar** a paleta; sempre prefira as utilities/tokens a hex literais.

## Paleta Oficial

A identidade visual v3 do BHUB é uma paleta **quente** — borgonha como marca,
sage/olive como acento, tan e cream de apoio sobre um canvas off-white. Transmite
seriedade acadêmica com calor humano (Social & Behavioral Sciences).

### Cores principais

```
🍷 Borgonha  #58272d  → MARCA — botões, links, CTAs, headings (primary-600)
🌿 Sage      #a3a16e  → acento secundário — barras de relevância, links em dark (sage-400)
🟤 Tan       #a48c68  → tom de terra de apoio — ornamentos, contornos (tan-400)
🟡 Cream     #f0eebd  → fundos suaves (hero, citações) — NUNCA em texto (cream-200)
⚪ Paper     #f4f0f1  → canvas da página (paper)
```

### Escala primária (burgundy)

| Token | Hex | Uso |
|-------|-----|-----|
| `primary-50` | `#fbf3f4` | lavagem de hover, fundos tintados |
| `primary-100` | `#f4dedf` | chips, bordas claras |
| `primary-500` | `#7e3640` | estados intermediários |
| `primary-600` | `#58272d` | **★ marca** — CTAs, links, ícones |
| `primary-700` | `#4a1f24` | hover |
| `primary-900` | `#2a1115` | headings / texto profundo |

Acentos: `sage-{50..700}`, `tan-{50..600}`, `cream-{50..400}`. O ramo `slate-*`
do Tailwind foi remapeado para **stone quente** — qualquer `slate-*` existente já
aquece automaticamente.

---

## Regras de uso

- **Texto:** use `primary-900/700/600` (escuros) ou `slate-600/500` (corpo). **Nunca** use `cream-*`, `sage-400` ou `tan-400` como texto sobre fundo claro — são tons médios/claros, reservados a fundos, barras e ornamentos.
- **Marca/CTA:** `bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white`.
- **Acento:** `sage-600/700` para texto/ícones de acento; `sage-400` só para barras/preenchimentos.
- **Fundos suaves:** `bg-cream-100/200` (hero, blocos tintados) e `bg-paper` (canvas).
- **Métricas/dados:** classe `font-data` (Elms Sans) + `tabular-nums`.

### Exemplos

```html
<!-- Botão primário (marca) -->
<button class="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-xl transition-colors">
  Explorar Artigos
</button>

<!-- Card sobre fundo suave -->
<div class="bg-cream-100 border border-cream-300 rounded-2xl p-6">
  <h3 class="text-primary-900 font-bold">Título do Card</h3>
  <p class="text-slate-600">Conteúdo do card…</p>
</div>

<!-- Acento sage (barra de relevância) -->
<div class="h-2 rounded-full bg-slate-100">
  <div class="h-full rounded-full bg-sage-400" style="width: 72%"></div>
</div>

<!-- Métrica (Elms Sans) -->
<span class="font-data tabular-nums text-3xl font-bold text-primary-700">681</span>
```

---

## Chips de categoria (soft-tint)

Cada categoria tem um trio `bg`/`fg`/`bd` (fundo claro + texto saturado + borda),
definido como `--cat-*` em `design-tokens.css` — ex.: clínica, pesquisa, educação,
organizacional, autismo, behaviorismo, verbal, notícias, outros. Use sempre esses
tokens em vez de cores avulsas para manter consistência.

---

## Cores semânticas (feedback)

Afinadas à paleta quente (escala `*-50/100/500/600/700`):

| Papel | 500 | Uso |
|-------|-----|-----|
| `success` | `#74894a` (olive) | confirmações, sync ok |
| `warning` | `#c79434` (gold) | avisos, atenção |
| `error` | `#b34a52` (warm rose) | erros, ações destrutivas |
| `info` | `#5a7f72` (sage-teal) | informações, dicas |

---

## Tipografia

| Família | Token | Papel |
|---------|-------|-------|
| Reddit Sans | `font-sans` / `--font-sans` | UI / corpo |
| Chivo Mono | `font-mono` / `--font-mono` | código, paths, tokens |
| Georgia | `font-serif` / `--font-serif` | headlines de artigo |
| Elms Sans | `font-data` / `--font-data` | dados / métricas |

Todas **self-hosted** (sem Google Fonts CDN) — ver
[`app/static/fonts/README.md`](../../bhub-backend-python/app/static/fonts/README.md).

---

## Modo escuro

Quente (borgonha + stone profundo), não frio. As semânticas trocam via
`[data-theme="dark"]` em `design-tokens.css`: `--color-bg-primary` → stone-800,
`--color-text-primary` → paper, acentos passam a cream/sage. Use os tokens
semânticos (`--color-bg-*`, `--color-text-*`) em vez de hex fixos para que o dark
mode funcione automaticamente.

---

## Contraste / acessibilidade

Diretrizes (verificar sempre com ferramenta — ver recursos):

- ✅ `text-white` sobre `primary-600/700/800/900` → alto contraste (texto normal AA/AAA).
- ✅ `primary-900/700` sobre `paper`/`white`/`cream-*` → alto contraste.
- ⚠️ `sage-400`/`tan-400`/`cream-*` têm luminância média/alta — **não** usar como texto sobre claro; só como fundo, barra ou ornamento.

Mais detalhes em [VERIFICAÇÃO_CONTRASTE_CORES.md](./VERIFICAÇÃO_CONTRASTE_CORES.md).

---

## Recursos

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Tailwind Customizing Colors](https://tailwindcss.com/docs/customizing-colors)

---

**Última atualização:** Junho 2026
**Versão da paleta:** 3.0 (quente borgonha/sage)
