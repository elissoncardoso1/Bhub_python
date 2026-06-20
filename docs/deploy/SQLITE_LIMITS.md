# Limites e Considerações - SQLite em Produção

**Versão**: 1.0.0  
**Data**: Janeiro 2025

---

## 📋 Visão Geral

Este documento descreve os limites do SQLite e quando considerar migração para PostgreSQL em produção.

---

## ✅ SQLite é Adequado Para

### BETA/STAGING
- ✅ Ambiente controlado
- ✅ Tráfego baixo (< 100 req/min)
- ✅ 1 instância/servidor
- ✅ Tamanho do banco < 1GB
- ✅ Escrita < 1000 writes/segundo
- ✅ Alta disponibilidade não crítica

### PRODUÇÃO (Condições)
- ✅ Tráfego moderado (< 1000 req/min)
- ✅ 1 instância única
- ✅ Tamanho do banco < 1GB
- ✅ Escrita < 1000 writes/segundo
- ✅ Backup automático configurado
- ✅ Monitoramento ativo

---

## ⚠️ Limites do SQLite

### Concorrência

**Limite prático**: ~1000 writes/segundo

**Considerações**:
- SQLite usa file locking
- Múltiplos writers podem causar contenção
- WAL mode melhora performance, mas não remove limite

**Configuração atual**:
```python
# app/database.py
PRAGMA journal_mode=WAL
PRAGMA synchronous=NORMAL
PRAGMA busy_timeout=30000  # 30 segundos
```

### Tamanho

**Limite teórico**: 281 TB  
**Limite prático recomendado**: < 1GB

**Considerações**:
- Performance degrada com tamanho
- Backup/restore fica mais lento
- Índices ocupam espaço adicional

### Escalabilidade

**Limite**: 1 servidor/instância

**Considerações**:
- SQLite não suporta múltiplos servidores
- Não há replicação nativa
- Load balancing não é possível

### Funcionalidades

**Limitações**:
- Sem usuários/roles nativos
- Sem stored procedures
- Sem triggers avançados (limitado)
- Sem particionamento

---

## 🚨 Quando Migrar para PostgreSQL

### Critérios de Migração

Migre para PostgreSQL quando **QUALQUER** condição abaixo for verdadeira:

1. **Tráfego**: > 1000 requisições/minuto
2. **Escrita**: > 1000 writes/segundo
3. **Tamanho**: Banco > 1GB
4. **Servidores**: Necessidade de múltiplos servidores
5. **Alta Disponibilidade**: Requisito crítico
6. **Replicação**: Necessidade de réplicas
7. **Concorrência**: Múltiplos writers simultâneos frequentes

### Sinais de Alerta

Monitore estes indicadores:

- **Lock timeouts frequentes**: `database is locked` nos logs
- **Performance degradada**: Queries > 1s regularmente
- **Tamanho crescente**: Banco crescendo > 100MB/mês
- **Backup lento**: Backup > 5 minutos
- **Erros de concorrência**: Múltiplos erros de lock

---

## 🔧 Otimizações Atuais

### WAL Mode

```sql
PRAGMA journal_mode=WAL;
```

**Benefícios**:
- Melhor concorrência (readers não bloqueiam writers)
- Performance melhorada
- Reduz contenção

### Busy Timeout

```sql
PRAGMA busy_timeout=30000;
```

**Benefícios**:
- Retry automático em caso de lock
- Reduz erros de "database is locked"
- Timeout de 30 segundos

### Synchronous Normal

```sql
PRAGMA synchronous=NORMAL;
```

**Benefícios**:
- Balance entre segurança e performance
- Adequado para produção com backups

---

## 📊 Estratégia de Backup

### Backup Automático

- **Frequência**: Diária (2h da manhã)
- **Retenção**: 30 dias (beta), 90 dias (produção)
- **Verificação**: Integridade antes e depois
- **Localização**: `backups/bhub_backup_YYYYMMDD_HHMMSS.db`

### Restore

- **Tempo estimado**: < 5 minutos (banco < 1GB)
- **Downtime**: Necessário durante restore
- **Procedimento**: Documentado em `RUNBOOK.md`

---

## 🔄 Plano de Migração (Futuro)

### Quando Necessário

1. **Preparação**
   - Criar schema PostgreSQL equivalente
   - Scripts de migração de dados
   - Testes em ambiente de staging

2. **Migração**
   - Backup completo do SQLite
   - Export de dados
   - Import no PostgreSQL
   - Validação de integridade

3. **Rollback**
   - Manter SQLite como backup
   - Procedimento de rollback documentado

### Estimativa

- **Tempo**: 2-4 horas (dependendo do tamanho)
- **Downtime**: 1-2 horas
- **Risco**: Médio (com backup e rollback)

---

## 📝 Recomendações

### Para BETA

✅ **SQLite é adequado**:
- Ambiente controlado
- Tráfego baixo
- 1 instância
- Backup automático configurado

### Para PRODUÇÃO (Inicial)

✅ **SQLite pode ser adequado se**:
- Tráfego < 1000 req/min
- Tamanho < 1GB
- 1 instância única
- Monitoramento ativo

⚠️ **Planejar migração se**:
- Crescimento rápido previsto
- Necessidade de alta disponibilidade
- Múltiplos servidores

### Para PRODUÇÃO (Escala)

❌ **Migrar para PostgreSQL quando**:
- Qualquer critério de migração for atingido
- Alta disponibilidade for crítica
- Múltiplos servidores necessários

---

## 🔍 Monitoramento

### Métricas a Monitorar

1. **Tamanho do banco**: Alertar se > 500MB
2. **Tempo de queries**: Alertar se > 1s
3. **Locks**: Alertar se frequentes
4. **Backup**: Verificar execução diária
5. **Integridade**: Verificar semanalmente

### Comandos Úteis

```bash
# Tamanho do banco
ls -lh bhub.db

# Estatísticas
sqlite3 bhub.db "SELECT COUNT(*) FROM articles;"

# Verificar integridade
sqlite3 bhub.db "PRAGMA integrity_check;"

# Verificar locks
sqlite3 bhub.db "PRAGMA busy_timeout;"
```

---

## 📚 Referências

- [SQLite Limits](https://www.sqlite.org/limits.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [When to Use SQLite](https://www.sqlite.org/whentouse.html)

---

**Última atualização**: Janeiro 2025
