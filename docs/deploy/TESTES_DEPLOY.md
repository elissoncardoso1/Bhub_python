# Testes e Deploy - Quando Executar

**Versão**: 1.0.0  
**Data**: Janeiro 2025

---

## 📋 Resumo

**Os testes automatizados (`pytest`) devem ser executados ANTES do deploy, não no VPS.**

---

## ✅ Onde Executar Testes

### 1. Ambiente Local (Recomendado)

**Quando**: Antes de fazer commit/push

```bash
cd bhub-backend-python

# Instalar dependências de teste (se necessário)
pip install -r requirements.txt
# Isso inclui: pytest, pytest-asyncio, pytest-cov

# ou para desenvolvimento completo:
# pip install -r requirements-dev.txt

# Todos os testes
pytest tests/ -v

# Testes específicos
pytest tests/test_smoke.py -v
pytest tests/test_e2e.py -v
pytest tests/test_permissions.py -v
pytest tests/test_rate_limit.py -v
pytest tests/test_csrf.py -v

# Com cobertura
pytest tests/ -v --cov=app --cov-report=html
```

**Vantagens**:
- Rápido
- Feedback imediato
- Não consome recursos do servidor

---

### 2. CI/CD (Futuro)

**Quando**: Automaticamente no push/PR

**Exemplo (GitHub Actions)**:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

**Vantagens**:
- Automático
- Valida antes de merge
- Histórico de execuções

---

### 3. VPS (NÃO Recomendado)

**❌ NÃO execute a suíte completa de testes no VPS**

**Por quê?**:
- Consome recursos do servidor
- Pode impactar performance
- Testes podem modificar dados (mesmo em banco de teste)
- Não é necessário para validação pós-deploy

**O que fazer no VPS**:
- ✅ Health check: `curl http://localhost:8000/health`
- ✅ Verificar logs: `docker-compose logs backend`
- ✅ Testar endpoints críticos manualmente
- ✅ Validar backup/restore

---

## 🔄 Fluxo Recomendado

### Antes do Deploy

1. **Desenvolvimento Local**
   ```bash
   # Fazer mudanças no código
   # Executar testes
   pytest tests/ -v
   
   # Se passar, commit
   git add .
   git commit -m "feat: nova feature"
   ```

2. **CI/CD (se configurado)**
   - Testes executam automaticamente
   - Se passar, pode fazer deploy

3. **Deploy**
   ```bash
   # No servidor
   git pull
   docker-compose up -d --build
   ```

### Após Deploy

1. **Validação Básica no VPS**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Verificar logs
   docker-compose logs --tail=50 backend
   
   # Testar endpoints críticos
   curl http://localhost:8000/api/v1/articles
   ```

2. **Monitoramento**
   - Verificar logs continuamente
   - Monitorar health check
   - Validar funcionalidades manualmente

---

## 📊 Checklist de Testes

### Antes do Deploy (Local/CI)

- [ ] Testes smoke: `pytest tests/test_smoke.py -v`
- [ ] Testes E2E: `pytest tests/test_e2e.py -v`
- [ ] Testes permissões: `pytest tests/test_permissions.py -v`
- [ ] Testes rate limit: `pytest tests/test_rate_limit.py -v`
- [ ] Testes CSRF: `pytest tests/test_csrf.py -v`
- [ ] Cobertura mínima: `pytest --cov=app --cov-report=html`

### Após Deploy (VPS)

- [ ] Health check responde: `curl http://localhost:8000/health`
- [ ] Logs sem erros críticos: `docker-compose logs backend | grep ERROR`
- [ ] Endpoints críticos funcionam (teste manual)
- [ ] Scheduler rodando (verificar logs)
- [ ] Backup funcionando: `python -m scripts.backup_db`

---

## 🚨 Exceções

### Testes de Integração no VPS

**Apenas se necessário**:
- Testes que requerem ambiente específico do VPS
- Validação de configuração específica
- Testes de performance/load

**Como executar (se necessário)**:
```bash
# Dentro do container
docker-compose exec backend pytest tests/test_smoke.py -v

# Ou criar banco de teste separado
docker-compose exec backend pytest tests/ -v --db-url=sqlite+aiosqlite:///./test.db
```

**⚠️ CUIDADO**: 
- Não execute testes que modificam dados em produção
- Use banco de teste separado
- Execute apenas quando necessário

---

## 📝 Resumo

| Ambiente | Quando | O Que Executar |
|----------|--------|----------------|
| **Local** | Antes de commit | Todos os testes (`pytest tests/ -v`) |
| **CI/CD** | No push/PR | Todos os testes (automático) |
| **VPS** | Após deploy | Apenas health check e validações básicas |

---

**Última atualização**: Janeiro 2025
