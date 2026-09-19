# 📚 Documentação BHUB

Bem-vindo à documentação do projeto BHUB. Esta pasta reúne toda a documentação
organizada por categoria.

**Comece por aqui:**

- 🏗️ **[architecture/CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md)** — **a única
  referência da arquitetura atual**: componentes, limites dos módulos, banco (dev vs produção),
  worker, scheduler, busca, IA, ingestão, observabilidade, deploy, e ainda os blocos PLANNED,
  DEFERRED, KNOWN RISKS e HISTORICAL. Decisões: [`adr/`](./adr/).
- 🗺️ **[architecture/ROADMAP.md](./architecture/ROADMAP.md)** — o que está declarado como trabalho
  aberto (plano do ciclo v1.1, itens adiados, riscos conhecidos).
- 🤖 **[AGENTS.md](../AGENTS.md)** · **[CLAUDE.md](../CLAUDE.md)** — contexto para agentes de
  código: comandos, convenções e as regras que não se negociam.

**Regra de leitura:** documentos com o banner `STATUS: HISTÓRICO` descrevem fases anteriores e
**não** são a arquitetura atual — em particular, itens não marcados de planos históricos **não**
são backlog aberto. Os documentos sob as seções "Histórico" abaixo estão nessa categoria.
Não use `ESTADO_ATUAL_PROJETO.md` nem os guias em `arquitetura/` como descrição do presente.

---

## 📂 Estrutura da Documentação

### 🏗️ Arquitetura — [`architecture/`](./architecture/) · [`arquitetura/`](./arquitetura/)

Referências atuais:

- **[architecture/CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md)** — arquitetura atual (referência única)
- **[architecture/ROADMAP.md](./architecture/ROADMAP.md)** — trabalho declarado
- **[adr/](./adr/)** — ADRs 0001–0005 (banco, fila de jobs, busca, monolito modular, IA)
- **[architecture/SERVICE_INSTANTIATION_MAP.md](./architecture/SERVICE_INSTANTIATION_MAP.md)** · **[architecture/GLOBAL_SINGLETONS.md](./architecture/GLOBAL_SINGLETONS.md)** — mapa de instanciação de serviços e decisões sobre singletons (Épico 2)

<details><summary><strong>Histórico — guias da migração Next.js → Python (era SQLite)</strong></summary>

- **[arquitetura/MIGRATION_GUIDE.md](./arquitetura/MIGRATION_GUIDE.md)** — migração de Next.js para Python/FastAPI (**histórico**)
- **[arquitetura/MIGRATION_GUIDE_BACKEND.md](./arquitetura/MIGRATION_GUIDE_BACKEND.md)** — guia específico do backend (**histórico**)
- **[arquitetura/bhub-stack-recomendada.md](./arquitetura/bhub-stack-recomendada.md)** — stack recomendada daquela fase (**histórico**)
- **[arquitetura/bhub-design-reference.md](./arquitetura/bhub-design-reference.md)** — design da fase anterior à paleta v3 (**histórico**)

</details>

### 🔧 Configuração — [`configuracao/`](./configuracao/)

- **[configuracao/ANALYTICS.md](./configuracao/ANALYTICS.md)** — sistema de analytics (eventos, sessões, métricas)
- **[configuracao/FEEDS_RSS.md](./configuracao/FEEDS_RSS.md)** — configuração de feeds RSS
- **[configuracao/LOCAL_LLM_SETUP.md](./configuracao/LOCAL_LLM_SETUP.md)** — setup do LLM local (Phi-3-mini / llama.cpp)

<details><summary><strong>Histórico</strong></summary>

- **[configuracao/DOCUMENTACAO_BACKEND.md](./configuracao/DOCUMENTACAO_BACKEND.md)** — documentação completa do backend escrita em dez/2024, **antes** da migração para PostgreSQL (**histórico**; a configuração atual está em CURRENT_ARCHITECTURE § 3 e § 10)
- **[configuracao/GUIA_INICIO_RAPIDO.md](./configuracao/GUIA_INICIO_RAPIDO.md)** — início rápido do plano de UI/UX de jan/2025, com a paleta daquela fase (**histórico**)
- **[configuracao/prompt_tradutor.md](./configuracao/prompt_tradutor.md)** — prompt/especificação da tradução com cache, escrita para a arquitetura frontend TypeScript + backend Python daquela fase (**histórico**; a implementação atual é `app/services/translation_cache_service.py`)

</details>

### 🚀 Deploy — [`deploy/`](./deploy/)

Atual:

- **[deploy/RUNBOOK.md](./deploy/RUNBOOK.md)** — runbook operacional de produção (PostgreSQL 16: backup/restore com `pg_dump`/`pg_restore`, migrações, incidentes)
- **[deploy/SECURITY_DECISIONS.md](./deploy/SECURITY_DECISIONS.md)** — decisões de segurança tomadas na preparação do deploy

<details><summary><strong>Histórico — era SQLite e era frontend Next.js separado</strong></summary>

- **[deploy/SQLITE_LIMITS.md](./deploy/SQLITE_LIMITS.md)** — limites do SQLite e quando migrar para PostgreSQL (**histórico**; a produção é PostgreSQL 16 — ADR-0001)
- **[deploy/DEPLOY_PROD.md](./deploy/DEPLOY_PROD.md)** · **[deploy/DEPLOY_STAGING.md](./deploy/DEPLOY_STAGING.md)** · **[deploy/CHECKLIST_GO_NOGO.md](./deploy/CHECKLIST_GO_NOGO.md)** · **[deploy/MAPA_EXECUCAO_DEPLOY.md](./deploy/MAPA_EXECUCAO_DEPLOY.md)** — checklists e pipelines daquela fase (**histórico**)
- **[deploy/VPS_DEPLOY.md](./deploy/VPS_DEPLOY.md)** · **[deploy/VPS_UPLOAD.md](./deploy/VPS_UPLOAD.md)** · **[deploy/VPS_MAINTENANCE.md](./deploy/VPS_MAINTENANCE.md)** — VPS com PM2/frontend separado e backup em arquivo SQLite (**histórico**; o procedimento atual é o RUNBOOK)
- **[deploy/DOCKER_DEPLOY.md](./deploy/DOCKER_DEPLOY.md)** · **[deploy/README_DOCKER.md](./deploy/README_DOCKER.md)** · [deploy/deploy-docker.sh](./deploy/deploy-docker.sh) — deploy com o `docker-compose.prod.yml` da **raiz** (backend + `./Frontend`, que não existe neste repositório) (**histórico**; o deploy atual usa `bhub-backend-python/docker-compose.prod.yml`)
- **[deploy/RESUMO_IMPLEMENTACAO.md](./deploy/RESUMO_IMPLEMENTACAO.md)** — resumo da implementação de jan/2025 (**histórico**)
- **[deploy/TESTES_DEPLOY.md](./deploy/TESTES_DEPLOY.md)** · **[deploy/TESTES_FINAL.md](./deploy/TESTES_FINAL.md)** · **[deploy/TESTES_RESULTADO.md](./deploy/TESTES_RESULTADO.md)** — resultados de teste de jan/2025 (**histórico**)

</details>

### 🔒 Segurança — [`seguranca/`](./seguranca/)

- **[seguranca/SECURITY_AUDIT.md](./seguranca/SECURITY_AUDIT.md)** — auditoria completa
- **[seguranca/SECURITY_REMAINING.md](./seguranca/SECURITY_REMAINING.md)** — itens pendentes
- **[seguranca/SECURITY_FIXES_CRITICAL.md](./seguranca/SECURITY_FIXES_CRITICAL.md)** · **[seguranca/SECURITY_FIXES_HIGH.md](./seguranca/SECURITY_FIXES_HIGH.md)** — correções por severidade
- **[seguranca/CVE-2025-55182_FIX.md](./seguranca/CVE-2025-55182_FIX.md)** — correção de CVE específica
- **[seguranca/CORS_FIX.md](./seguranca/CORS_FIX.md)** — correções de CORS
- **[seguranca/PRIVACIDADE_COOKIES.md](./seguranca/PRIVACIDADE_COOKIES.md)** — camada de consentimento de cookies (LGPD): cookie `bhub_consent`, gate do analytics, cookies em uso, como testar/estender

### 🎨 UI/UX — [`ui-ux/`](./ui-ux/)

**Design system (v3 — paleta quente borgonha/sage):**

- **[ui-ux/PALETA_CORES.md](./ui-ux/PALETA_CORES.md)** — paleta oficial e tokens de cor
- Fonte canônica dos tokens: [`app/static/css/design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css) · config Tailwind: [`tailwind.config.js`](../bhub-backend-python/tailwind.config.js)
- Fontes self-hosted (Reddit Sans · Chivo Mono · Elms Sans): [`app/static/fonts/README.md`](../bhub-backend-python/app/static/fonts/README.md)
- **[ui-ux/CONVENCAO_TAILWIND_CSS.md](./ui-ux/CONVENCAO_TAILWIND_CSS.md)** — convenções de uso do Tailwind
- **[ui-ux/VERIFICAÇÃO_CONTRASTE_CORES.md](./ui-ux/VERIFICAÇÃO_CONTRASTE_CORES.md)** — verificação de contraste/acessibilidade
- **[ui-ux/FOOTER_REFACTOR_2026.md](./ui-ux/FOOTER_REFACTOR_2026.md)** — refatoração do footer

**Guias e análises:**

- **[ui-ux/UI_UX_SETUP.md](./ui-ux/UI_UX_SETUP.md)** · **[ui-ux/UI_UX_COMPONENT_EXAMPLES.md](./ui-ux/UI_UX_COMPONENT_EXAMPLES.md)** · **[ui-ux/UI_UX_MELHORIAS_COMPONENTES.md](./ui-ux/UI_UX_MELHORIAS_COMPONENTES.md)** · **[ui-ux/UI_UX_REVISAO_MCP.md](./ui-ux/UI_UX_REVISAO_MCP.md)**
- **[ui-ux/UI_UX_BUSCA_AVANCADA_PROBLEMAS.md](./ui-ux/UI_UX_BUSCA_AVANCADA_PROBLEMAS.md)** · **[ui-ux/UI_UX_BUSCA_AVANCADA_CORRECOES.md](./ui-ux/UI_UX_BUSCA_AVANCADA_CORRECOES.md)** — busca avançada
- **[ui-ux/INTEGRAÇÃO_ANIMEJS.md](./ui-ux/INTEGRAÇÃO_ANIMEJS.md)** — animações (Anime.js)

**Acessibilidade e responsividade (fases):**

- **[ui-ux/FASE_1_2_ACESSIBILIDADE.md](./ui-ux/FASE_1_2_ACESSIBILIDADE.md)** · **[ui-ux/FASE_2_2_COMPONENTES_FEEDBACK.md](./ui-ux/FASE_2_2_COMPONENTES_FEEDBACK.md)** · **[ui-ux/FASE_2_3_RESPONSIVIDADE_MOBILE.md](./ui-ux/FASE_2_3_RESPONSIVIDADE_MOBILE.md)** · **[ui-ux/FASE_3_APRIMORAMENTOS_UX.md](./ui-ux/FASE_3_APRIMORAMENTOS_UX.md)**

<details><summary><strong>Diffs e auditorias do refactor de CSS/tokens (registros de trabalho executado)</strong></summary>

- **[ui-ux/UI_UX_ANALYSIS.md](./ui-ux/UI_UX_ANALYSIS.md)** — análise de jan/2025 que declara a paleta **teal/verde-água** como oficial; foi substituída pela v3 ([PALETA_CORES.md](./ui-ux/PALETA_CORES.md)) (**histórico**)
- **[ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md](./ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md)** — plano hierárquico de UI/UX (**histórico**)
- [AUDITORIA_CSS_REFACTOR.md](./ui-ux/AUDITORIA_CSS_REFACTOR.md) · [APP_CSS_REFACTOR_DIFF.md](./ui-ux/APP_CSS_REFACTOR_DIFF.md) · [GOVERANCA_TAILWIND_CSS_DIFF.md](./ui-ux/GOVERANCA_TAILWIND_CSS_DIFF.md)
- [ARTICLE_CARD_MIGRATION_DIFF.md](./ui-ux/ARTICLE_CARD_MIGRATION_DIFF.md) · [ACESSIBILIDADE_CONSOLIDACAO_DIFF.md](./ui-ux/ACESSIBILIDADE_CONSOLIDACAO_DIFF.md)
- [PASSO_1_FOCUS_STYLES_DIFF.md](./ui-ux/PASSO_1_FOCUS_STYLES_DIFF.md) · [TOAST_DURATION_SYNC_DIFF.md](./ui-ux/TOAST_DURATION_SYNC_DIFF.md)

</details>

### ⚙️ Implementação — [`implementacao/`](./implementacao/)

Registros de funcionalidades que existem no código:

- **[implementacao/IMPLEMENTACAO_TRADUCAO.md](./implementacao/IMPLEMENTACAO_TRADUCAO.md)** — sistema de tradução automática
- **[implementacao/OPEN_GRAPH_IMPLEMENTATION.md](./implementacao/OPEN_GRAPH_IMPLEMENTATION.md)** · **[implementacao/OPEN_GRAPH_RESUMO.md](./implementacao/OPEN_GRAPH_RESUMO.md)** — Open Graph / social meta
- **[implementacao/HTMX_FIX_SUMMARY.md](./implementacao/HTMX_FIX_SUMMARY.md)** — correções HTMX

<details><summary><strong>Histórico — checklists, progresso e próximos passos de jan/2025</strong></summary>

- **[implementacao/CHECKLIST_IMPLEMENTACAO.md](./implementacao/CHECKLIST_IMPLEMENTACAO.md)** · **[implementacao/PROGRESSO_IMPLEMENTACAO.md](./implementacao/PROGRESSO_IMPLEMENTACAO.md)** · **[implementacao/PRÓXIMOS_PASSOS.md](./implementacao/PRÓXIMOS_PASSOS.md)** — plano de UI/UX e seu acompanhamento (**histórico**; os itens não marcados não são backlog aberto — ver [ROADMAP.md](./architecture/ROADMAP.md))
- **[implementacao/IMPLEMENTAÇÃO_PRIORIDADE_ALTA.md](./implementacao/IMPLEMENTAÇÃO_PRIORIDADE_ALTA.md)** — relatório de implementação de jan/2025 (**histórico**)

</details>

### ♻️ Refatoração — [`refatoracao/`](./refatoracao/)

- **[refatoracao/ARTICLE_CARD_COMPACT_ALIGNMENT.md](./refatoracao/ARTICLE_CARD_COMPACT_ALIGNMENT.md)** — alinhamento compacto do card de artigo
- **[refatoracao/ARTICLE_DETAIL_REFACTOR.md](./refatoracao/ARTICLE_DETAIL_REFACTOR.md)** — refatoração da página de detalhe do artigo

### 🧪 Qualidade — [`quality/`](./quality/)

- **[quality/BASELINE.md](./quality/BASELINE.md)** — baseline de qualidade e limites declarados dos gates de CI (Ruff, mypy, cobertura, ratchet, build da imagem)
- **[quality/RELEASE_CHECKLIST_v1.1.md](./quality/RELEASE_CHECKLIST_v1.1.md)** — verificação de código do checklist de release da v1.1 (Task 19), item por item, com status GO/NO-GO parcial, evidência e riscos conhecidos

---

## 🗺️ Navegação Rápida

### Para Desenvolvedores

1. **Começando**: [AGENTS.md](../AGENTS.md) → [CLAUDE.md](../CLAUDE.md) → [README do projeto](../README.md)
2. **Arquitetura**: [architecture/CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md) e [adr/](./adr/); o trabalho declarado está em [architecture/ROADMAP.md](./architecture/ROADMAP.md)
3. **Configuração**: [architecture/CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md) § 3 (banco), § 10 (deploy) e [CLAUDE.md](../CLAUDE.md) (variáveis de ambiente)

### Para DevOps

1. **Deploy**: [deploy/RUNBOOK.md](./deploy/RUNBOOK.md) (é o procedimento vigente: PostgreSQL 16)
2. **Go/No-Go**: [deploy/CHECKLIST_GO_NOGO.md](./deploy/CHECKLIST_GO_NOGO.md) (_histórico_ — a lista era da era SQLite)
3. **Segurança**: [seguranca/SECURITY_AUDIT.md](./seguranca/SECURITY_AUDIT.md) e [seguranca/SECURITY_REMAINING.md](./seguranca/SECURITY_REMAINING.md)

### Para Designers/UI

1. **Paleta e tokens v3**: [ui-ux/PALETA_CORES.md](./ui-ux/PALETA_CORES.md) + [`design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css)
2. **Convenções**: [ui-ux/CONVENCAO_TAILWIND_CSS.md](./ui-ux/CONVENCAO_TAILWIND_CSS.md)
3. **Análise e plano**: [ui-ux/UI_UX_ANALYSIS.md](./ui-ux/UI_UX_ANALYSIS.md) e [ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md](./ui-ux/PLANO_IMPLEMENTACAO_UI_UX.md) — ambos **históricos** (paleta teal anterior); para o estado atual use [CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md) § 1 e [PALETA_CORES.md](./ui-ux/PALETA_CORES.md)

### Para Gestores de Projeto

1. **Estado atual**: [architecture/CURRENT_ARCHITECTURE.md](./architecture/CURRENT_ARCHITECTURE.md) — `ESTADO_ATUAL_PROJETO.md` é **histórico** (análise de dez/2024)
2. **Trabalho aberto**: [architecture/ROADMAP.md](./architecture/ROADMAP.md)
3. **Progresso**: [implementacao/PROGRESSO_IMPLEMENTACAO.md](./implementacao/PROGRESSO_IMPLEMENTACAO.md) e [implementacao/PRÓXIMOS_PASSOS.md](./implementacao/PRÓXIMOS_PASSOS.md) — **históricos** (jan/2025); o andamento do ciclo v1.1 fica em `.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/progress.md` (diretório de trabalho, não versionado)

---

## 📝 Convenções

- Documentação em Markdown (`.md`), com links relativos para facilitar a navegação.
- Tokens de design vivem no código ([`design-tokens.css`](../bhub-backend-python/app/static/css/design-tokens.css) / [`tailwind.config.js`](../bhub-backend-python/tailwind.config.js)); a documentação de UI deve referenciá-los, não duplicar valores.
- Documentos devem ser atualizados conforme o projeto evolui.
- Documento que descreve uma fase encerrada recebe, no topo, o banner
  `> STATUS: HISTÓRICO` + `> Este documento não representa necessariamente a arquitetura atual.` +
  `> Consulte docs/architecture/CURRENT_ARCHITECTURE.md.` — e continua versionado (histórico não
  se apaga para simplificar o índice).

---

**Última atualização**: Setembro 2026
