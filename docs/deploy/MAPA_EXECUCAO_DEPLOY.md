# Mapa de Execução - Deploy BHUB

**Data**: Janeiro 2025  
**Versão**: 1.0.0  
**Objetivo**: Preparar BHUB para deploy em BETA (GO) e PRODUÇÃO (NO-GO até fechar bloqueadores)

---

## 🎯 Visão Geral

### BETA/STAGING (GO agora)
- **Status**: ✅ Pronto para deploy controlado
- **Cenário**: 1 instância, tráfego controlado, acesso restrito
- **Requisitos**: Funcionalidades básicas + segurança mínima + testes smoke

### PRODUÇÃO PÚBLICA (NO-GO até fechar bloqueadores)
- **Status**: ⚠️ Bloqueado até resolver MUST-HAVES
- **Cenário**: Tráfego público, múltiplos usuários, alta disponibilidade
- **Requisitos**: Todos os MUST-HAVES + testes completos + operação robusta

---

## 📋 Trilha BETA (GO agora)

### ✅ Tarefas Críticas para BETA

| # | Tarefa | Arquivos Impactados | Risco | Validação |
|---|--------|---------------------|-------|-----------|
| 1 | Testes smoke básicos | `tests/test_smoke.py` | Baixo | `pytest tests/test_smoke.py -v` |
| 2 | Health check funcional | `app/main.py` | Baixo | `curl http://localhost:8000/health` |
| 3 | Scheduler com lock (prevenir duplicação) | `app/jobs/scheduler.py`, `app/config.py` | Médio | Teste com 2 processos |
| 4 | Backup automático SQLite | `scripts/backup_db.py` | Baixo | Script executável + restore testado |
| 5 | Logs estruturados básicos | `app/core/logging.py` | Baixo | Verificar formato JSON |
| 6 | Documentação deploy staging | `docs/deploy/DEPLOY_STAGING.md` | Baixo | Passo a passo testado |

**Critérios de Aceite BETA:**
- ✅ `/health` responde corretamente
- ✅ Testes smoke passam
- ✅ Scheduler não duplica jobs
- ✅ Backup automático funciona
- ✅ Logs são gerados corretamente

---

## 🚫 Trilha PRODUÇÃO (Bloqueadores - NO-GO)

### 🔴 MUST-HAVES (Bloqueadores)

| # | Tarefa | Arquivos Impactados | Risco | Validação | Status |
|---|--------|---------------------|-------|-----------|--------|
| 1 | **Testes completos** | `tests/` | Alto | Cobertura mínima 60% | ⚠️ Em progresso |
| 1.1 | Smoke test `/health` | `tests/test_smoke.py` | Baixo | `pytest tests/test_smoke.py::test_health` | ✅ |
| 1.2 | E2E: login → admin → sync → upload | `tests/test_e2e.py` | Médio | `pytest tests/test_e2e.py` | ⚠️ |
| 1.3 | Permissões USER vs ADMIN | `tests/test_permissions.py` | Alto | `pytest tests/test_permissions.py` | ⚠️ |
| 1.4 | Rate limit (borda) | `tests/test_rate_limit.py` | Médio | `pytest tests/test_rate_limit.py` | ⚠️ |
| 1.5 | CSRF (borda) | `tests/test_csrf.py` | Alto | `pytest tests/test_csrf.py` | ⚠️ |
| 2 | **Segurança: SECURITY_REMAINING** | `docs/seguranca/` | Alto | Todos itens resolvidos/justificados | ⚠️ |
| 2.1 | Revisar e classificar severidade | `docs/seguranca/SECURITY_REMAINING.md` | Médio | Documento atualizado | ⚠️ |
| 2.2 | Resolver ou justificar cada item | Vários | Alto | `SECURITY_DECISIONS.md` criado | ⚠️ |
| 2.3 | Validar CSRF, sessões, headers | `app/core/` | Alto | Testes automatizados | ⚠️ |
| 3 | **Scheduler sem duplicação** | `app/jobs/scheduler.py` | Alto | Teste com 2 processos | ⚠️ |
| 3.1 | Implementar lock distribuído | `app/jobs/scheduler.py` | Médio | Teste de integração | ⚠️ |
| 3.2 | Env var SCHEDULER_MODE | `app/config.py` | Baixo | Validação de env | ⚠️ |
| 4 | **SQLite: limites + operação** | `docs/`, `scripts/` | Alto | Documentação + backup/restore | ⚠️ |
| 4.1 | Documentar limites SQLite | `docs/deploy/SQLITE_LIMITS.md` | Baixo | Documento claro | ⚠️ |
| 4.2 | Backup automático + retenção | `scripts/backup_db.py` | Médio | Script testado | ⚠️ |
| 4.3 | Restore testado | `scripts/restore_db.py` | Médio | Procedimento validado | ⚠️ |
| 4.4 | Concorrência (pragmas) | `app/database.py` | Médio | Testes de carga | ⚠️ |
| 5 | **Operação: logs + alertas** | `app/core/logging.py`, `scripts/` | Alto | Logs estruturados + alertas | ⚠️ |
| 5.1 | Logs estruturados (JSON) | `app/core/logging.py` | Baixo | Formato JSON válido | ⚠️ |
| 5.2 | Alertas mínimos (health, jobs, DB) | `scripts/alerts.py` ou pluggable | Médio | Alertas funcionais | ⚠️ |
| 5.3 | Runbook básico | `docs/deploy/RUNBOOK.md` | Baixo | Procedimentos documentados | ⚠️ |

### 🟡 SHOULD-HAVES (Não bloqueia BETA, mas importante para PROD)

| # | Tarefa | Arquivos Impactados | Risco | Validação | Status |
|---|--------|---------------------|-------|-----------|--------|
| 6 | Timeouts/retries/circuit-breaker IA | `app/ai/`, `app/services/` | Médio | Testes de resiliência | ⚠️ |
| 7 | Cache e deduplicação | `app/services/` | Baixo | Testes de cache | ⚠️ |
| 8 | Otimização queries/índices | `app/models/`, `alembic/` | Médio | Análise de performance | ⚠️ |
| 9 | CI/CD mínimo | `.github/workflows/` | Baixo | Pipeline funcional | ⚠️ |

---

## 📊 Resumo de Status

### BETA (GO)
- ✅ Health check
- ✅ Testes smoke básicos
- ⚠️ Scheduler com lock (em progresso)
- ⚠️ Backup automático (em progresso)
- ⚠️ Logs estruturados (em progresso)

### PRODUÇÃO (NO-GO)
- ⚠️ Testes completos (0/5)
- ⚠️ Segurança (0/3)
- ⚠️ Scheduler (0/2)
- ⚠️ SQLite (0/4)
- ⚠️ Operação (0/3)

---

## 🎯 Próximos Passos Imediatos

1. **Implementar testes smoke** (1-2h)
2. **Implementar scheduler lock** (2-3h)
3. **Implementar backup automático** (1-2h)
4. **Revisar SECURITY_REMAINING** (2-3h)
5. **Criar documentação deploy** (2-3h)

**Tempo estimado total**: 8-13 horas

---

## 📝 Notas

- **Cenário assumido**: Beta fechado em 1 VPS com Docker Compose
- **Volume estimado**: 
  - Feeds: ~29 feeds, sincronização a cada hora
  - Jobs: 1 job principal (sync feeds)
  - Uploads: Baixo volume inicial
- **IA**: DeepSeek/OpenRouter, limites desconhecidos (implementar timeouts/retries)
