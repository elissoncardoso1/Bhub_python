# ✅ Checklist de Implementação UI/UX

## 🔴 FASE 1: FUNDAÇÃO CRÍTICA (Semanas 1-2)

### 1.1. Unificar Design System e Implementar Paleta Oficial
- [ ] Criar `app/static/css/design-tokens.css` com paleta oficial
- [ ] Criar `tailwind.config.js` com paleta teal/verde-água
- [ ] Atualizar `base.html` com nova configuração
- [ ] Migrar `login.html` para Tailwind
- [ ] Deprecar `app.css` (documentar uso restante)

### 1.2. Acessibilidade Básica (WCAG 2.1 AA)
- [ ] Adicionar ARIA labels em botões sem texto
- [ ] Adicionar ARIA labels em links e formulários
- [ ] Implementar fechamento de modais com ESC
- [ ] Adicionar skip to main content link
- [ ] Criar classe `.sr-only` para screen readers
- [ ] Validar contraste de todas as combinações de cores
- [ ] Criar `app/static/css/accessibility.css`

### 1.3. Componentes Base Melhorados
- [ ] Melhorar componente de busca (label, ARIA, responsivo)
- [ ] Melhorar botão de fechar modal (ARIA, ESC, focus)
- [ ] Melhorar cards de artigos (semantic HTML, Schema.org)
- [ ] Atualizar helper de ícones para acessibilidade

---

## 🟠 FASE 2: PERFORMANCE E ESTABILIDADE (Semanas 2-3)

### 2.1. Otimizar Tailwind CSS (Produção)
- [ ] Instalar Tailwind CSS localmente (npm/yarn)
- [ ] Criar `postcss.config.js`
- [ ] Criar `app/static/css/input.css`
- [ ] Configurar scripts de build (dev e prod)
- [ ] Atualizar `base.html` para usar CSS compilado em produção

### 2.2. Componentes de Feedback
- [ ] Criar `app/templates/components/loading.html`
- [ ] Criar `app/templates/components/error.html`
- [ ] Criar `app/templates/components/empty.html`
- [ ] Integrar componentes em templates existentes
- [ ] Adicionar skeleton loaders

### 2.3. Responsividade Mobile
- [ ] Implementar menu hamburger na navbar
- [ ] Adicionar drawer/sidebar para mobile
- [ ] Criar busca mobile (botão que abre modal)
- [ ] Ajustar cards e grids para mobile
- [ ] Melhorar formulários mobile (touch targets)
- [ ] Testar em dispositivos reais

---

## 🟡 FASE 3: APRIMORAMENTOS DE UX (Semanas 4-5)

### 3.1. Micro-interações e Animações
- [ ] Adicionar transições suaves em hover states
- [ ] Implementar animações de entrada/saída
- [ ] Melhorar feedback visual de ações
- [ ] Respeitar `prefers-reduced-motion`
- [ ] Criar `app/static/css/animations.css`

### 3.2. Melhorias de Navegação
- [ ] Adicionar breadcrumbs onde necessário
- [ ] Melhorar design de paginação
- [ ] Implementar atalhos de teclado (`/` para busca, `Esc` para modais)
- [ ] Criar `app/static/js/keyboard-shortcuts.js`

### 3.3. SEO e Meta Tags
- [ ] Adicionar Open Graph tags em todas as páginas
- [ ] Implementar Twitter Cards
- [ ] Adicionar Schema.org structured data
- [ ] Melhorar meta descriptions
- [ ] Validar com Google Rich Results

---

## 🟢 FASE 4: FEATURES AVANÇADAS (Semanas 6-8)

### 4.1. Dark Mode
- [ ] Criar toggle de tema no navbar
- [ ] Implementar persistência (localStorage)
- [ ] Respeitar `prefers-color-scheme`
- [ ] Aplicar variáveis CSS de modo escuro
- [ ] Testar contraste em modo escuro
- [ ] Criar `app/static/js/theme-toggle.js`

### 4.2. Otimizações Avançadas
- [ ] Implementar lazy loading de imagens
- [ ] Adicionar placeholders/blur-up
- [ ] Configurar cache headers
- [ ] Versionamento de assets
- [ ] Otimizar imagens (WebP)

### 4.3. Polish Final e Documentação
- [ ] Revisão final de consistência visual
- [ ] Testes de acessibilidade (axe, WAVE)
- [ ] Testes de performance (Lighthouse)
- [ ] Testes cross-browser
- [ ] Documentação completa
- [ ] Changelog atualizado

---

## 📊 Progresso Geral

**Fase 1:** 0/15 tarefas concluídas  
**Fase 2:** 0/11 tarefas concluídas  
**Fase 3:** 0/8 tarefas concluídas  
**Fase 4:** 0/11 tarefas concluídas  

**Total:** 0/45 tarefas concluídas (0%)

---

## 🎯 Próximos Passos Imediatos

1. ✅ Ler `PLANO_IMPLEMENTACAO_UI_UX.md` completo
2. ⬜ Começar Fase 1.1: Criar `design-tokens.css`
3. ⬜ Configurar `tailwind.config.js` com paleta oficial
4. ⬜ Migrar primeira página (login.html)

---

**Última atualização:** 2025-01-19

