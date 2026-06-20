# Auditoria CSS/JS - Plano de Refactor

**Data:** 2026-01-26  
**Objetivo:** Consolidar design tokens, remover duplicações, unificar linguagem visual

---

## 1. LISTA DE CONFLITOS E DUPLICAÇÕES

### 1.1. **Sistema de Tokens Duplo (CRÍTICO)**

**Problema:** Dois sistemas de tokens competindo:

#### Sistema A: `app.css` (NÃO USADO, mas carregado?)
- `--bg: #0b1020` (azul escuro)
- `--panel: #121a33`
- `--text: #e6e8f2`
- `--brand: #7c3aed` (roxo)
- `--brand-2: #22d3ee` (ciano)
- `--radius: 14px`
- **Status:** Não está sendo carregado no `base.html` ❌

#### Sistema B: `design-tokens.css` (OFICIAL)
- `--color-primary-*` (teal #3fb5a3)
- `--color-bg-primary`, `--color-text-primary`
- `--radius-md`, `--space-*`
- **Status:** Carregado e usado parcialmente ✅

**Impacto:** `app.css` define tema dark roxo/ciano que conflita com tema teal oficial.

---

### 1.2. **Duplicação: `.sr-only`**

**Localizações:**
1. `accessibility.css` (linhas 2-12) ✅ **FONTE DA VERDADE**
2. `input.css` (linhas 7-17) - dentro de `@layer utilities` do Tailwind
3. `output.css` (compilado Tailwind) - gerado automaticamente

**Conflito:** Tailwind gera `.sr-only` automaticamente, mas temos definição manual.

**Decisão:** Manter apenas em `accessibility.css`. Remover de `input.css` (Tailwind já fornece via `@apply` ou classes utilitárias).

---

### 1.3. **Duplicação: `prefers-reduced-motion`**

**Localizações:**
1. `animations.css` (linhas 645-684) ✅ **FONTE DA VERDADE** (mais completo)
2. `responsive.css` (linhas 308-328) - regras específicas para mobile
3. `article-card.css` (linhas 651-677) - regras específicas para cards
4. `accessibility.css` - **REMOVIDO** (já consolidado)

**Conflito:** Múltiplas definições podem causar especificidade inconsistente.

**Decisão:** 
- Manter regra global em `animations.css`
- Manter regras específicas em `responsive.css` e `article-card.css` (complementam, não duplicam)

---

### 1.4. **Conflito: Focus Styles (outline vs ring)**

**Problema:** Dois sistemas de focus competindo:

#### Sistema A: CSS Manual (`accessibility.css`)
```css
*:focus-visible {
  outline: 2px solid var(--color-primary-400);
  outline-offset: 2px;
}
```

#### Sistema B: Tailwind Ring (`output.css`)
```css
.focus\:ring-2:focus { ... }
.ring-primary-400 { ... }
```

**Uso atual:**
- `article-card.css`: usa `outline` manual (5 ocorrências)
- `app.js`: usa classes Tailwind `focus:ring-2 focus:ring-error-500`
- `keyboard-shortcuts.js`: usa `ring-2 ring-primary-400` (Tailwind)

**Impacto:** Inconsistência visual entre elementos com focus.

**Decisão:** Unificar em **Tailwind ring** (mais flexível, já integrado).

---

### 1.5. **Cores Hardcoded vs Tokens**

#### `app.css` (NÃO CARREGADO)
- ❌ Todas as cores são hardcoded: `rgba(255, 255, 255, 0.10)`, `#0b1020`, etc.
- ❌ Não usa tokens semânticos

#### `article-card.css` (PARCIALMENTE MIGRADO)
- ✅ Maioria migrada para tokens
- ⚠️ Ainda tem cores hardcoded em:
  - Tags de categoria (cores específicas por categoria - OK manter)
  - Alguns fallbacks em `var()`: `var(--color-bg-primary, #ffffff)`

#### `responsive.css`
- ⚠️ Usa tokens com fallbacks: `var(--color-bg-primary, #0b3536)`
- ✅ Boa prática, mas fallbacks poderiam ser removidos após validação

---

### 1.6. **Conflito: Tema Dark**

**Problema:** Dois temas dark diferentes:

1. **`app.css`** (não carregado): Tema roxo/ciano escuro
2. **`design-tokens.css`**: Tema teal escuro (oficial)

**Status:** `app.css` não está sendo usado, então não há conflito real. Mas arquivo existe e pode causar confusão.

---

### 1.7. **Espaçamentos e Tipografia**

**Status:** ✅ Bem consolidado
- `design-tokens.css` define todos os tokens
- `article-card.css` usa tokens consistentemente
- `responsive.css` usa tokens

**Observação:** Alguns valores hardcoded em `app.css` (não usado).

---

## 2. PROPOSTA DE "FONTE DA VERDADE"

### 2.1. **Design Tokens** → `design-tokens.css`

**Responsabilidades:**
- ✅ Cores primárias (`--color-primary-*`)
- ✅ Cores semânticas (`--color-bg-*`, `--color-text-*`, `--color-border-*`)
- ✅ Cores de suporte (success, error, warning, info)
- ✅ Tipografia (`--font-*`, `--font-size-*`, `--font-weight-*`)
- ✅ Espaçamento (`--space-*`)
- ✅ Bordas (`--radius-*`)
- ✅ Sombras (`--shadow-*`)
- ✅ Transições (`--transition-*`)
- ✅ Dark mode (`@media (prefers-color-scheme: dark)`)

**Ordem de carregamento:** PRIMEIRO (antes de qualquer outro CSS)

---

### 2.2. **Acessibilidade** → `accessibility.css`

**Responsabilidades:**
- ✅ `.sr-only` (única definição)
- ✅ `*:focus-visible` (DEPRECAR - migrar para Tailwind ring)
- ✅ `.skip-to-main`
- ❌ `prefers-reduced-motion` (removido - consolidado em `animations.css`)

**Ações:**
- Manter `.sr-only`
- Remover `*:focus-visible` (deixar Tailwind gerenciar)
- Manter `.skip-to-main`

---

### 2.3. **Animações** → `animations.css`

**Responsabilidades:**
- ✅ Todas as animações CSS
- ✅ `prefers-reduced-motion` (regra global)
- ✅ Keyframes
- ✅ Utility classes de animação

---

### 2.4. **Responsividade** → `responsive.css`

**Responsabilidades:**
- ✅ Touch targets (WCAG)
- ✅ Safe areas (iOS)
- ✅ Breakpoints mobile
- ✅ `prefers-reduced-motion` (regras específicas mobile - complementar, não duplicar)

---

### 2.5. **Componentes** → `article-card.css`

**Responsabilidades:**
- ✅ Estilos específicos de cards
- ✅ Usar tokens de `design-tokens.css`
- ✅ Dark mode específico (se necessário)
- ✅ `prefers-reduced-motion` (regras específicas - complementar)

---

### 2.6. **Focus Styles** → Tailwind Ring (via `output.css`)

**Decisão:** Migrar de `outline` manual para Tailwind `ring-*`

**Vantagens:**
- Consistência com resto do sistema
- Mais flexível (ring-offset, ring-inset)
- Já está sendo usado em JS

**Ação:** Remover `*:focus-visible` de `accessibility.css`, usar classes Tailwind.

---

### 2.7. **`app.css`** → DECISÃO NECESSÁRIA

**Opções:**

**A) Remover completamente**
- ✅ Elimina confusão
- ✅ Não está sendo usado
- ⚠️ Pode ter estilos úteis (verificar antes)

**B) Migrar estilos úteis e remover**
- ✅ Preserva funcionalidade
- ⚠️ Trabalho adicional
- ⚠️ Risco de regressão

**C) Manter como "legacy" com comentário**
- ⚠️ Mantém arquivo morto
- ✅ Documenta histórico

**Recomendação:** **Opção A** - Remover completamente.

**Validação realizada:** 
- ✅ `app.css` NÃO está sendo carregado no `base.html`
- ✅ Nenhuma classe de `app.css` (`.panel`, `.btn`, `.card`, etc.) encontrada nos templates
- ✅ Arquivo pode ser removido com segurança

---

## 3. ORDEM DE EXECUÇÃO (4-6 PASSOS)

### **PASSO 1: Consolidar Focus Styles** 
**Risco:** 🟡 MÉDIO | **Impacto:** 🟢 BAIXO | **Tempo:** 30min

**Ações:**
1. Remover `*:focus-visible` de `accessibility.css`
2. Migrar `article-card.css` de `outline` para classes Tailwind `focus:ring-2 focus:ring-primary-400`
3. Adicionar `focus:outline-none` onde necessário (Tailwind padrão)
4. Testar navegação por teclado

**Validação:**
- [ ] Tab navigation funciona
- [ ] Focus visível em todos os elementos interativos
- [ ] Consistência visual entre elementos

---

### **PASSO 2: Remover Duplicação de `.sr-only`**
**Risco:** 🟢 BAIXO | **Impacto:** 🟢 BAIXO | **Tempo:** 15min

**Ações:**
1. Verificar se Tailwind já fornece `.sr-only` (sim, via `output.css`)
2. Remover definição de `input.css` (dentro de `@layer utilities`)
3. Manter apenas em `accessibility.css` OU usar Tailwind diretamente
4. Atualizar referências se necessário

**Validação:**
- [ ] `.sr-only` funciona em leitores de tela
- [ ] Sem regressões visuais

**Decisão:** Usar Tailwind `.sr-only` (já compilado) e remover de `accessibility.css` também? Ou manter em `accessibility.css` como fonte única?

---

### **PASSO 3: Auditar e Decidir sobre `app.css`**
**Risco:** 🟡 MÉDIO | **Impacto:** 🟡 MÉDIO | **Tempo:** 45min

**Ações:**
1. Verificar se `app.css` está sendo usado em algum lugar (grep por classes: `.panel`, `.btn`, `.card`, etc.)
2. Verificar se há estilos úteis que devem ser migrados
3. Se não usado: **remover arquivo**
4. Se usado: migrar estilos úteis para componentes específicos ou `design-tokens.css`

**Validação:**
- [ ] Nenhuma regressão visual após remoção/migração
- [ ] Funcionalidade preservada

---

### **PASSO 4: Consolidar `prefers-reduced-motion`**
**Risco:** 🟢 BAIXO | **Impacto:** 🟢 BAIXO | **Tempo:** 20min

**Ações:**
1. Manter regra global em `animations.css` (já está correto)
2. Verificar se regras em `responsive.css` e `article-card.css` são complementares (não duplicadas)
3. Adicionar comentários explicando hierarquia:
   - Global: `animations.css`
   - Mobile-specific: `responsive.css`
   - Component-specific: `article-card.css`

**Validação:**
- [ ] Reduced motion funciona corretamente
- [ ] Sem animações em `prefers-reduced-motion: reduce`

---

### **PASSO 5: Remover Fallbacks Hardcoded (Opcional)**
**Risco:** 🟡 MÉDIO | **Impacto:** 🟢 BAIXO | **Tempo:** 30min

**Ações:**
1. Remover fallbacks de `var()` após validar que tokens sempre existem
2. Exemplo: `var(--color-bg-primary, #ffffff)` → `var(--color-bg-primary)`
3. Fazer em arquivos específicos (não todos de uma vez)

**Validação:**
- [ ] Sem quebras visuais
- [ ] Dark mode funciona

**Nota:** Manter fallbacks pode ser boa prática para resiliência. Avaliar caso a caso.

---

### **PASSO 6: Documentar Sistema de Tokens**
**Risco:** 🟢 BAIXO | **Impacto:** 🟢 BAIXO | **Tempo:** 30min

**Ações:**
1. Adicionar comentários em `design-tokens.css` explicando hierarquia
2. Criar guia de uso (quando usar tokens vs classes Tailwind)
3. Documentar decisões de design (por que teal, não roxo)

**Validação:**
- [ ] Documentação clara para futuros desenvolvedores

---

## 4. RESUMO DE DECISÕES

| Item | Fonte da Verdade | Ação |
|------|------------------|------|
| **Cores** | `design-tokens.css` | ✅ Já consolidado |
| **Espaçamento** | `design-tokens.css` | ✅ Já consolidado |
| **Tipografia** | `design-tokens.css` | ✅ Já consolidado |
| **`.sr-only`** | Tailwind (`output.css`) OU `accessibility.css` | 🔄 Decidir: Tailwind ou manual? |
| **Focus styles** | Tailwind Ring | 🔄 Migrar de `outline` manual |
| **`prefers-reduced-motion`** | `animations.css` (global) + específicos | ✅ Já consolidado |
| **`app.css`** | ❌ Não usado | 🔄 Remover ou migrar |

---

## 5. CHECKLIST PRÉ-REFACTOR

Antes de começar, validar:

- [ ] Backup do código atual
- [ ] Testes manuais de acessibilidade (teclado, leitor de tela)
- [ ] Testes de dark mode
- [ ] Testes de reduced motion
- [ ] Verificar se `app.css` não está sendo usado (grep)

---

## 6. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Regressão visual | 🟡 Média | 🟡 Médio | Testes manuais após cada passo |
| Quebra de acessibilidade | 🟢 Baixa | 🔴 Alto | Testes com leitores de tela |
| Conflito Tailwind x CSS | 🟡 Média | 🟡 Médio | Usar apenas Tailwind para focus |
| Perda de funcionalidade | 🟢 Baixa | 🟡 Médio | Verificar uso de `app.css` antes de remover |

---

**Próximo passo:** Revisar este plano e aprovar ordem de execução antes de codar.
