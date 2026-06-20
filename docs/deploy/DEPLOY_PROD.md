# Deploy BHUB - Produção

**Versão**: 1.0.0  
**Data**: Janeiro 2025  
**Status**: ⚠️ **NO-GO** até fechar bloqueadores

---

## 🚫 Status Atual: BLOQUEADO

**Este ambiente NÃO está pronto para produção pública.**

### Bloqueadores (MUST-HAVES)

Antes de fazer deploy em produção, **TODOS** os itens abaixo devem estar resolvidos:

1. ✅ **Testes completos** (smoke, E2E, permissões, rate-limit, CSRF)
2. ⚠️ **Segurança**: Revisar e resolver/justificar todos os itens de `SECURITY_REMAINING.md`
3. ✅ **Scheduler**: Prevenção de duplicação implementada
4. ✅ **SQLite**: Limites documentados + backup/restore funcionando
5. ⚠️ **Operação**: Logs estruturados + alertas mínimos + runbook

**Ver detalhes em**: `MAPA_EXECUCAO_DEPLOY.md`

---

## 📋 Checklist GO/NO-GO

### ✅ GO para Produção (Todos devem estar ✅)

#### Testes
- [ ] Testes smoke passam (`pytest tests/test_smoke.py -v`)
- [ ] Testes E2E passam (`pytest tests/test_e2e.py -v`)
- [ ] Testes de permissões passam (`pytest tests/test_permissions.py -v`)
- [ ] Testes de rate limit passam (`pytest tests/test_rate_limit.py -v`)
- [ ] Testes de CSRF passam (`pytest tests/test_csrf.py -v`)
- [ ] Cobertura mínima de 60% (`pytest --cov=app --cov-report=html`)

#### Segurança
- [ ] `SECURITY_REMAINING.md` revisado
- [ ] Todos os itens ALTOS resolvidos ou justificados
- [ ] `SECURITY_DECISIONS.md` atualizado
- [ ] CSRF validado em todas as rotas mutáveis
- [ ] Sessões/cookies validados
- [ ] Headers de segurança validados

#### Scheduler
- [ ] Lock distribuído implementado e testado
- [ ] Teste de duplicação passa (2 processos simulados)
- [ ] `SCHEDULER_MODE` configurado corretamente

#### SQLite
- [ ] Limites documentados (`docs/deploy/SQLITE_LIMITS.md`)
- [ ] Backup automático funcionando
- [ ] Restore testado e validado
- [ ] Concorrência tratada (pragmas)

#### Operação
- [ ] Logs estruturados (JSON)
- [ ] Alertas mínimos implementados
- [ ] Runbook criado e testado
- [ ] Procedimentos de incidente documentados

### ❌ NO-GO (Se qualquer item acima estiver ❌)

**NÃO fazer deploy em produção até resolver todos os bloqueadores.**

---

## 🎯 Quando Estiver Pronto

### Pré-requisitos de Infraestrutura

- **Servidor**: Mínimo 4GB RAM, 4 CPUs, 50GB disco SSD
- **Backup**: Estratégia de backup automático + off-site
- **Monitoramento**: Sistema de alertas configurado
- **SSL/TLS**: Certificado válido (Let's Encrypt)
- **Firewall**: Configurado e restrito
- **DNS**: Configurado e validado

### Configuração de Ambiente

```env
# App
ENVIRONMENT=production
DEBUG=false

# Security (OBRIGATÓRIO: gerar nova chave!)
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
ALLOWED_ORIGINS=https://seu-dominio.com

# Scheduler
SCHEDULER_MODE=worker  # Worker separado em produção
ENABLE_SCHEDULER=true

# Backup
BACKUP_RETENTION_DAYS=90  # 3 meses em produção
```

### Processo de Deploy

1. **Preparação**
   ```bash
   # Backup completo
   docker-compose exec backend python -m scripts.backup_db
   
   # Verificar saúde
   curl https://seu-dominio.com/health
   ```

2. **Deploy**
   ```bash
   # Parar aplicação
   docker-compose -f docker-compose.prod.yml down
   
   # Atualizar código
   git pull origin main
   
   # Migrações
   docker-compose run --rm backend alembic upgrade head
   
   # Rebuild
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

3. **Validação**
   ```bash
   # Health check
   curl https://seu-dominio.com/health
   
   # Verificar logs
   docker-compose logs -f backend
   
   # Testes smoke
   pytest tests/test_smoke.py -v
   ```

---

## 🔒 Segurança em Produção

### Checklist Obrigatório

- [ ] SECRET_KEY gerado com `openssl rand -hex 32`
- [ ] DEBUG=false
- [ ] ALLOWED_ORIGINS configurado (sem wildcards)
- [ ] SSL/TLS configurado (HTTPS obrigatório)
- [ ] Firewall configurado
- [ ] Acesso SSH restrito (chaves, não senha)
- [ ] Backups automáticos + off-site
- [ ] Logs sendo monitorados
- [ ] Alertas configurados
- [ ] Rate limiting ativo
- [ ] CSRF protection ativo
- [ ] CORS restrito

---

## 📊 Monitoramento

### Métricas Essenciais

- **Health check**: `/health` a cada 30s
- **Logs de erro**: Monitorar nível ERROR
- **Uso de recursos**: CPU, memória, disco
- **Tamanho do banco**: Alertar se > 1GB
- **Backups**: Verificar execução diária
- **Scheduler**: Verificar execução de jobs

### Alertas Mínimos

1. **App fora do ar**: Health check falha 3x consecutivas
2. **Job falhando**: Scheduler job falha 2x consecutivas
3. **DB lock/corrompido**: Erro de integridade
4. **Quota IA**: Limite de API atingido
5. **Disco cheio**: > 80% uso

---

## 🚨 Procedimentos de Emergência

### App Fora do Ar

1. Verificar logs: `docker-compose logs backend`
2. Verificar recursos: `docker stats`
3. Restart: `docker-compose restart backend`
4. Se persistir: Restaurar backup

### Banco Corrompido

1. Parar aplicação
2. Restaurar último backup: `python -m scripts.restore_db backups/bhub_backup_YYYYMMDD_HHMMSS.db`
3. Verificar integridade
4. Reiniciar aplicação

### Scheduler Duplicando

1. Verificar locks: `SELECT * FROM scheduler_locks;`
2. Limpar locks expirados manualmente se necessário
3. Verificar `SCHEDULER_MODE` (deve ser `worker` em produção)

---

## 📝 Limites e Considerações

### SQLite em Produção

**⚠️ IMPORTANTE**: SQLite tem limitações para produção pública:

- **Concorrência**: Máximo ~1000 writes/segundo
- **Tamanho**: Recomendado < 1GB (máximo teórico 281TB)
- **Escalabilidade**: Não adequado para múltiplos servidores

**Quando migrar para PostgreSQL**:
- Tráfego > 1000 req/min
- Múltiplos servidores
- Necessidade de alta disponibilidade
- Tamanho do banco > 1GB

Ver: `docs/deploy/SQLITE_LIMITS.md`

---

## 🔄 Roadmap Pós-Deploy

### Melhorias Prioritárias

1. **Migração para PostgreSQL** (quando necessário)
2. **CI/CD completo** (GitHub Actions)
3. **Monitoramento avançado** (Prometheus + Grafana)
4. **Alertas robustos** (PagerDuty/Sentry)
5. **Backup off-site** automatizado
6. **Testes de carga** regulares

---

## 📞 Suporte

Em caso de problemas:
1. Consultar `RUNBOOK.md`
2. Verificar logs
3. Consultar `SECURITY_DECISIONS.md` para decisões de segurança
4. Abrir issue no repositório

---

**⚠️ LEMBRE-SE**: Este ambiente está **BLOQUEADO** até fechar todos os bloqueadores listados em `MAPA_EXECUCAO_DEPLOY.md`.

**Última atualização**: Janeiro 2025
