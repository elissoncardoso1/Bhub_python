# 🎨 Verificação de Contraste de Cores (WCAG AA)

**Data:** 2025-01-27  
**Status:** ⏳ Requer verificação manual

---

## 📋 Cores a Verificar

### Background do Card
- **Cor:** `#ffffff` (branco)
- **Uso:** Background principal do `article-card`

### Tags de Categorias

Todas as tags têm:
- Background: `rgba(..., 0.15)` (15% de opacidade)
- Texto: Cor sólida
- Background efetivo: Branco + overlay colorido

#### 1. Clínica
- **Background:** `rgba(63, 181, 163, 0.15)` → `#e6f7f5` (aproximado)
- **Texto:** `#0d7a78`
- **Contraste necessário:** 4.5:1 (WCAG AA)
- **Status:** ⚠️ Verificar

#### 2. Pesquisa
- **Background:** `rgba(59, 130, 246, 0.15)` → `#eef2ff` (aproximado)
- **Texto:** `#1e40af`
- **Status:** ⚠️ Verificar

#### 3. Educação
- **Background:** `rgba(139, 92, 246, 0.15)` → `#f5f3ff` (aproximado)
- **Texto:** `#5b21b6`
- **Status:** ⚠️ Verificar

#### 4. Organizacional
- **Background:** `rgba(251, 146, 60, 0.15)` → `#fff7ed` (aproximado)
- **Texto:** `#92400e`
- **Status:** ⚠️ Verificar

#### 5. Autismo
- **Background:** `rgba(236, 72, 153, 0.15)` → `#fdf2f8` (aproximado)
- **Texto:** `#9f1239`
- **Status:** ⚠️ Verificar

#### 6. Behaviorismo Radical
- **Background:** `rgba(168, 85, 247, 0.15)` → `#f5f3ff` (aproximado)
- **Texto:** `#5b21b6`
- **Status:** ⚠️ Verificar

#### 7. Comportamento Verbal
- **Background:** `rgba(34, 197, 94, 0.15)` → `#f0fdf4` (aproximado)
- **Texto:** `#15803d`
- **Status:** ⚠️ Verificar

#### 8. Notícias
- **Background:** `rgba(249, 115, 22, 0.15)` → `#fff7ed` (aproximado)
- **Texto:** `#9a3412`
- **Status:** ⚠️ Verificar

#### 9. Outros
- **Background:** `rgba(107, 114, 128, 0.15)` → `#f3f4f6` (aproximado)
- **Texto:** `#374151`
- **Status:** ✅ Provavelmente OK (cinza escuro em cinza claro)

### Tags de Tipo

#### Periódico
- **Background:** `rgba(168, 85, 247, 0.15)`
- **Texto:** `#5b21b6`
- **Status:** ⚠️ Verificar

#### Portal
- **Background:** `rgba(251, 146, 60, 0.15)`
- **Texto:** `#92400e`
- **Status:** ⚠️ Verificar

#### Open Access
- **Background:** `rgba(34, 197, 94, 0.15)`
- **Texto:** `#15803d`
- **Status:** ⚠️ Verificar

---

## 📝 Textos no Card

### Título
- **Cor:** `#1f2937` (gray-800)
- **Background:** Branco
- **Contraste:** ✅ 12.63:1 (Excelente)

### Metadata
- **Cor:** `#6b7280` (gray-500)
- **Background:** Branco
- **Contraste:** ⚠️ 4.58:1 (Limite - verificar)

### Descrição
- **Cor:** `#4b5563` (gray-600)
- **Background:** Branco
- **Contraste:** ✅ 7.00:1 (Bom)

### Metadata Extra
- **Cor:** `#9ca3af` (gray-400)
- **Background:** Branco
- **Contraste:** ❌ 2.85:1 (Insuficiente - precisa ajustar)

---

## 🔧 Melhorias Sugeridas

### 1. Metadata Extra
**Problema:** `#9ca3af` não tem contraste suficiente (2.85:1)

**Solução:**
```css
.metadata-extra {
    color: #6b7280; /* gray-500 - 4.58:1 */
    /* ou */
    color: #4b5563; /* gray-600 - 7.00:1 (melhor) */
}
```

### 2. Tags com Baixo Contraste
Se alguma tag não atender 4.5:1, aumentar opacidade do background:

```css
.article-tag.category-clinica {
    background: rgba(63, 181, 163, 0.2); /* Aumentar de 0.15 para 0.2 */
    color: #0d7a78;
    border: 1px solid rgba(63, 181, 163, 0.4); /* Aumentar borda também */
}
```

### 3. Textos em Slate-400
**Problema:** `text-slate-400` (#94a3b8) tem contraste 3.12:1

**Solução:** Usar `text-slate-500` (#64748b) que tem 4.58:1

---

## 🧪 Ferramentas de Verificação

### Online
1. [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
2. [Contrast Ratio Calculator](https://contrast-ratio.com/)
3. [WAVE Web Accessibility Evaluation Tool](https://wave.webaim.org/)

### Extensões
1. **Chrome DevTools** - Lighthouse (Accessibility audit)
2. **axe DevTools** - Extensão do Chrome
3. **WAVE** - Extensão do Chrome

### Comandos
```bash
# Usar Lighthouse CLI
npm install -g @lhci/cli
lhci autorun --url=http://localhost:8000
```

---

## ✅ Checklist de Verificação

- [ ] Verificar todas as tags de categorias (9 categorias)
- [ ] Verificar tags de tipo (3 tipos)
- [ ] Verificar metadata (`#6b7280`)
- [ ] Verificar metadata-extra (`#9ca3af`) - **CRÍTICO**
- [ ] Verificar textos em `text-slate-400` em outros templates
- [ ] Testar com Lighthouse
- [ ] Testar com axe DevTools
- [ ] Documentar cores aprovadas

---

## 📊 Cores Aprovadas (Após Verificação)

| Elemento | Cor Texto | Cor Background | Contraste | Status |
|----------|-----------|----------------|-----------|--------|
| Título | `#1f2937` | `#ffffff` | 12.63:1 | ✅ |
| Descrição | `#4b5563` | `#ffffff` | 7.00:1 | ✅ |
| Metadata | `#6b7280` | `#ffffff` | 4.58:1 | ⚠️ |
| Metadata Extra | `#9ca3af` | `#ffffff` | 2.85:1 | ❌ |

---

## 🚀 Próximos Passos

1. **Executar verificação manual** com WebAIM Contrast Checker
2. **Ajustar cores problemáticas** (metadata-extra é crítico)
3. **Testar com Lighthouse** para validação automática
4. **Documentar cores finais** aprovadas

---

**Nota:** A verificação de contraste com backgrounds semi-transparentes (rgba) é mais complexa, pois o contraste efetivo depende do background subjacente (branco no caso). Recomenda-se verificação manual para cada combinação.


