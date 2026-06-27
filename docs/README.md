# 📚 Documentação BHUB

Bem-vindo à documentação do projeto BHUB. Esta pasta reúne toda a documentação
organizada por categoria. Para orientação operacional do dia a dia (comandos,
arquitetura resumida, convenções de código), veja também o
**[CLAUDE.md](../CLAUDE.md)** na raiz do repositório.

## 📖 Documento Principal

**[ESTADO_ATUAL_PROJETO.md](./ESTADO_ATUAL_PROJETO.md)** — visão completa do estado atual do projeto: arquitetura, funcionalidades, estrutura e próximos passos.

---

## 📂 Estrutura da Documentação

### 🏗️ Arquitetura — [`arquitetura/`](./arquitetura/)

- **[MIGRATION_GUIDE.md](./arquitetura/MIGRATION_GUIDE.md)** — migração de Next.js para Python/FastAPI
- **[MIGRATION_GUIDE_BACKEND.md](./arquitetura/MIGRATION_GUIDE_BACKEND.md)** — guia específico do backend
- **[bhub-stack-recomendada.md](./arquitetura/bhub-stack-recomendada.md)** — stack tecnológica recomendada
- **[bhub-design-reference.md](./arquitetura/bhub-design-reference.md)** — referência de design do projeto

### 🔧 Configuração — [`configuracao/`](./configuracao/)

- **[GUIA_INICIO_RAPIDO.md](./configuracao/GUIA_INICIO_RAPIDO.md)** — guia de início rápido
- **[DOCUMENTACAO_BACKEND.md](./configuracao/DOCUMENTACAO_BACKEND.md)** — documentação completa do backend
- **[FEEDS_RSS.md](./configuracao/FEEDS_RSS.md)** — configuração de feeds RSS
- **[ANALYTICS.md](./configuracao/ANALYTICS.md)** — sistema de analytics (eventos, sessões, métricas)
- **[LOCAL_LLM_SETUP.md](./configuracao/LOCAL_LLM_SETUP.md)** — setup do LLM local (Phi-3-mini / llama.cpp)
- **[prompt_tradutor.md](./configuracao/prompt_tradutor.md)** — prompt de tradução

### 🚀 Deploy — [`deploy/`](./deploy/)

- **[DOCKER_DEPLOY.md](./deploy/DOCKER_DEPLOY.md)** · **[README_DOCKER.md](./deploy/README_DOCKER.md)** · **[deploy-docker.sh](./deploy/deploy-docker.sh)** — deploy com Docker
- **[VPS_DEPLOY.md](./deploy/VPS_DEPLOY.md)** · **[VPS_UPLOAD.md](./deploy/VPS_UPLOAD.md)** · **[VPS_MAINTENANCE.md](./deploy/VPS_MAINTENANCE.md)** — deploy e manutenção em VPS
- **[DEPLOY_STAGING.md](./deploy/DEPLOY_STAGING.md)** · **[DEPLOY_PROD.md](./deploy/DEPLOY_PROD.md)** — pipelines de staging e produção
- **[MAPA_EXECUCAO_DEPLOY.md](./deploy/MAPA_EXECUCAO_DEPLOY.md)** · **[CHECKLIST_GO_NOGO.md](./deploy/CHECKLIST_GO_NOGO.md)** · **[RUNBOOK.md](./deploy/RUNBOOK.md)** — execução, go/no-go e runbook operacional
- **[SECURITY_DECISIONS.md](./deploy/SECURITY_DECISIONS.md)** — decisões de segurança de deploy
- **[SQLITE_LIMITS.md](./deploy/SQLITE_LIMITS.md)** — limites do SQLite e quando migrar para PostgreSQL
- **[RESUMO_IMPLEMENTACAO.md](./deploy/RESUMO_IMPLEMENTACAO.md)** · **[TESTES_DEPLOY.md](./deploy/TESTES_DEPLOY.md)** · **[TESTES_FINAL.md](./deploy/TESTES_FINAL.md)** · **[TESTES_RESULTADO.md](./deploy/TESTES_RESULTADO.md)** — testes de deploy

### 🔒 Segurança — [`seguranca/`](./seguranca/)

- **[SECURITY_AUDIT.md](./seguranca/SECURITY_AUDIT.md)** — auditoria completa
- **[SECURITY_REMAINING.md](./seguranca/SECURITY_REMAINING.md)** — itens pendentes
- **[SECURITY_FIXES_CRITICAL.md](./seguranca/SECURITY_FIXES_CRITICAL.md)** · **[SECURITY_FIXES_HIGH.md](./seguranca/SECURITY_FIXES_HIGH.md)** — correções por severidade
- **[CVE-2025-55182_FIX.md](./seguranca/CVE-2025-55182_FIX.md)** — correção de CVE específica
- **[CORS_FIX.md](./seguranca/CORS_FIX.md)** — correções de CORS

### 🎨 UI/UX — [`ui-ux/`](./ui-ux/)

**Design system (v3 — paleta quente borgonha/sage):**

- **[PALETA_CORES.md](./ui-ux/PALETA_CORES.md)** — paleta oficial e tokens de cor
- Fonte canônica dos tokens: [`app/static/css/design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css) · config Tailwind: [`tailwind.config.js`](../bhub-backend-python/tailwind.config.js)
- Fontes self-hosted (Reddit Sans · Chivo Mono · Elms Sans): [`app/static/fonts/README.md`](../bhub-backend-python/app/static/fonts/README.md)
- **[CONVENCAO_TAILWIND_CSS.md](./ui-ux/CONVENCAO_TAILWIND_CSS.md)** — convenções de uso do Tailwind
- **[VERIFICAÇÃO_CONTRASTE_CORES.md](./ui-ux/VERIFICAÇÃO_CONTRASTE_CORES.md)** — verificação de contraste/acessibilidade

**Guias e análises:**

- **[UI_UX_ANALYSIS.md](./ui-ux/UI_UX_ANALYSIS.md)** · **[PLANO_IMPLEMENTACAO_UI_UX.md](./ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md)** · **[UI_UX_SETUP.md](./ui-ux/UI_UX_SETUP.md)**
- **[UI_UX_MELHORIAS_COMPONENTES.md](./ui-ux/UI_UX_MELHORIAS_COMPONENTES.md)** · **[UI_UX_COMPONENT_EXAMPLES.md](./ui-ux/UI_UX_COMPONENT_EXAMPLES.md)** · **[UI_UX_REVISAO_MCP.md](./ui-ux/UI_UX_REVISAO_MCP.md)**
- **[UI_UX_BUSCA_AVANCADA_PROBLEMAS.md](./ui-ux/UI_UX_BUSCA_AVANCADA_PROBLEMAS.md)** · **[UI_UX_BUSCA_AVANCADA_CORRECOES.md](./ui-ux/UI_UX_BUSCA_AVANCADA_CORRECOES.md)** — busca avançada
- **[INTEGRAÇÃO_ANIMEJS.md](./ui-ux/INTEGRAÇÃO_ANIMEJS.md)** — animações (Anime.js)
- **[FOOTER_REFACTOR_2026.md](./ui-ux/FOOTER_REFACTOR_2026.md)** — refatoração do footer

**Acessibilidade e responsividade (fases):**

- **[FASE_1_2_ACESSIBILIDADE.md](./ui-ux/FASE_1_2_ACESSIBILIDADE.md)** · **[FASE_2_2_COMPONENTES_FEEDBACK.md](./ui-ux/FASE_2_2_COMPONENTES_FEEDBACK.md)** · **[FASE_2_3_RESPONSIVIDADE_MOBILE.md](./ui-ux/FASE_2_3_RESPONSIVIDADE_MOBILE.md)** · **[FASE_3_APRIMORAMENTOS_UX.md](./ui-ux/FASE_3_APRIMORAMENTOS_UX.md)**

<details><summary><strong>Histórico de refatoração CSS (diffs e auditorias)</strong></summary>

- [AUDITORIA_CSS_REFACTOR.md](./ui-ux/AUDITORIA_CSS_REFACTOR.md) · [APP_CSS_REFACTOR_DIFF.md](./ui-ux/APP_CSS_REFACTOR_DIFF.md) · [GOVERANCA_TAILWIND_CSS_DIFF.md](./ui-ux/GOVERANCA_TAILWIND_CSS_DIFF.md)
- [ARTICLE_CARD_MIGRATION_DIFF.md](./ui-ux/ARTICLE_CARD_MIGRATION_DIFF.md) · [ACESSIBILIDADE_CONSOLIDACAO_DIFF.md](./ui-ux/ACESSIBILIDADE_CONSOLIDACAO_DIFF.md)
- [PASSO_1_FOCUS_STYLES_DIFF.md](./ui-ux/PASSO_1_FOCUS_STYLES_DIFF.md) · [TOAST_DURATION_SYNC_DIFF.md](./ui-ux/TOAST_DURATION_SYNC_DIFF.md)

</details>

### ⚙️ Implementação — [`implementacao/`](./implementacao/)

- **[CHECKLIST_IMPLEMENTACAO.md](./implementacao/CHECKLIST_IMPLEMENTACAO.md)** · **[PROGRESSO_IMPLEMENTACAO.md](./implementacao/PROGRESSO_IMPLEMENTACAO.md)** · **[PRÓXIMOS_PASSOS.md](./implementacao/PRÓXIMOS_PASSOS.md)**
- **[IMPLEMENTAÇÃO_PRIORIDADE_ALTA.md](./implementacao/IMPLEMENTAÇÃO_PRIORIDADE_ALTA.md)** — implementações de alta prioridade
- **[IMPLEMENTACAO_TRADUCAO.md](./implementacao/IMPLEMENTACAO_TRADUCAO.md)** — sistema de tradução automática
- **[OPEN_GRAPH_IMPLEMENTATION.md](./implementacao/OPEN_GRAPH_IMPLEMENTATION.md)** · **[OPEN_GRAPH_RESUMO.md](./implementacao/OPEN_GRAPH_RESUMO.md)** — Open Graph / social meta
- **[HTMX_FIX_SUMMARY.md](./implementacao/HTMX_FIX_SUMMARY.md)** — correções HTMX

### ♻️ Refatoração — [`refatoracao/`](./refatoracao/)

- **[ARTICLE_CARD_COMPACT_ALIGNMENT.md](./refatoracao/ARTICLE_CARD_COMPACT_ALIGNMENT.md)** — alinhamento compacto do card de artigo
- **[ARTICLE_DETAIL_REFACTOR.md](./refatoracao/ARTICLE_DETAIL_REFACTOR.md)** — refatoração da página de detalhe do artigo

---

## 🗺️ Navegação Rápida

### Para Desenvolvedores

1. **Começando**: [ESTADO_ATUAL_PROJETO.md](./ESTADO_ATUAL_PROJETO.md) → [GUIA_INICIO_RAPIDO.md](./configuracao/GUIA_INICIO_RAPIDO.md) → [CLAUDE.md](../CLAUDE.md)
2. **Arquitetura**: [MIGRATION_GUIDE.md](./arquitetura/MIGRATION_GUIDE.md) e [bhub-stack-recomendada.md](./arquitetura/bhub-stack-recomendada.md)
3. **Configuração**: [DOCUMENTACAO_BACKEND.md](./configuracao/DOCUMENTACAO_BACKEND.md)

### Para DevOps

1. **Deploy**: [DOCKER_DEPLOY.md](./deploy/DOCKER_DEPLOY.md) ou [VPS_DEPLOY.md](./deploy/VPS_DEPLOY.md) → [RUNBOOK.md](./deploy/RUNBOOK.md)
2. **Go/No-Go**: [CHECKLIST_GO_NOGO.md](./deploy/CHECKLIST_GO_NOGO.md)
3. **Segurança**: [SECURITY_AUDIT.md](./seguranca/SECURITY_AUDIT.md) e [SECURITY_REMAINING.md](./seguranca/SECURITY_REMAINING.md)

### Para Designers/UI

1. **Paleta e tokens v3**: [PALETA_CORES.md](./ui-ux/PALETA_CORES.md) + [`design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css)
2. **Convenções**: [CONVENCAO_TAILWIND_CSS.md](./ui-ux/CONVENCAO_TAILWIND_CSS.md)
3. **Análise e plano**: [UI_UX_ANALYSIS.md](./ui-ux/UI_UX_ANALYSIS.md) e [PLANO_IMPLEMENTACAO_UI_UX.md](./ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md)

### Para Gestores de Projeto

1. **Estado atual**: [ESTADO_ATUAL_PROJETO.md](./ESTADO_ATUAL_PROJETO.md)
2. **Progresso**: [PROGRESSO_IMPLEMENTACAO.md](./implementacao/PROGRESSO_IMPLEMENTACAO.md)
3. **Próximos passos**: [PRÓXIMOS_PASSOS.md](./implementacao/PRÓXIMOS_PASSOS.md)

---

## 📝 Convenções

- Documentação em Markdown (`.md`), com links relativos para facilitar a navegação.
- Tokens de design vivem no código ([`design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css) / [`tailwind.config.js`](../bhub-backend-python/tailwind.config.js)); a documentação de UI deve referenciá-los, não duplicar valores.
- Documentos devem ser atualizados conforme o projeto evolui.

---

**Última atualização**: Junho 2026
