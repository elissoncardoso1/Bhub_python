# Decisões de Segurança - BHUB

**Versão**: 1.0.0  
**Data**: Janeiro 2026

---

## 📋 Visão Geral

Este documento registra as decisões de segurança tomadas durante o desenvolvimento e preparação para deploy do BHUB. Cada item de `SECURITY_REMAINING.md` foi revisado e classificado como:
- ✅ **Resolvido**: Implementado e testado
- ⚠️ **Aceito**: Risco aceito com justificativa
- 📝 **Backlog**: Planejado para implementação futura

---

## ✅ Atualizações (Jan/2026)

- CSRF validado em rotas mutáveis via dependência global (se cookie presente)
- Logs estruturados JSON disponíveis via `LOG_JSON=true` (ou em produção)
- Alertas mínimos via webhook (`ALERT_WEBHOOK_URL`)
- Uploads de PDF com nome UUID e validação de caminho base

---

## 🔴 Vulnerabilidades Críticas

### CRIT-001: Rate Limiting ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Rate limiting global configurado (100 req/min)
- Rate limiting específico para rotas de IA (10/min)
- Rate limiting para endpoint de cron (3/hora)

**Validação**: Testes em `tests/test_rate_limit.py`

---

### CRIT-002: Sanitização FTS5 ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Whitelist approach para caracteres permitidos
- Remoção de palavras reservadas FTS5
- Limitação de termos e tamanho de query

**Validação**: Testes de busca validam sanitização

---

### CRIT-003: HttpOnly Cookies ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Cookies HttpOnly configurados
- Secure flag em produção
- SameSite=strict

**Validação**: Inspeção de cookies em navegador

---

## 🟠 Vulnerabilidades Altas

### HIGH-001: Validação de PDF ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Validação de tipo (magic bytes)
- Validação de tamanho (50MB)
- Validação de estrutura

---

### HIGH-002: CORS Restringido ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- CORS configurado com origens explícitas
- Sem wildcards em produção
- Validação automática em produção

---

### HIGH-003: Rate Limiting IA ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Janeiro 2026

**Implementação Atual**:
- Rate limiting básico (10/min) ✅
- Quota diária por usuário/IP (ex.: 100/dia) ✅
- Timeout curto para chamadas de IA (30s) ✅
- Limite de tamanho do texto para IA externa ✅

**Decisão**:
- **Aceito para PROD**: Controles mínimos de custo e abuso implementados

**Justificativa**:
- Combinação de quota diária e limite por minuto reduz abuso
- Timeout curto evita uso excessivo de recursos

---

### HIGH-004: Sanitização de Logs ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Sanitização de dados sensíveis em logs
- IPs anonimizados automaticamente

---

### HIGH-005: Validação SSRF ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Validação de URLs em scraping
- Bloqueio de IPs privados/localhost

---

### HIGH-006: Refresh Tokens ✅ RESOLVIDO

**Status**: ✅ Implementado  
**Data**: Dezembro 2024

**Implementação**:
- Sistema completo de refresh tokens
- Rotação de tokens
- Revogação em logout

**Nota**: Blacklist de tokens (Redis) deixado como backlog para produção avançada

---

### HIGH-007: Proteção CSRF ✅ RESOLVIDO

**Status**: ✅ Implementado (Backend)  
**Data**: Dezembro 2024

**Implementação**:
- Sistema completo de CSRF protection
- Tokens gerados automaticamente
- Validação via dependência

**Nota**: Integração completa no frontend deixada como backlog

---

### HIGH-008: Path Traversal ⚠️ ACEITO (Parcial)

**Status**: ⚠️ Parcialmente corrigido  
**Data**: Janeiro 2025

**Implementação Atual**:
- Sanitização básica ✅
- Validação com `Path.resolve()` ❌
- UUIDs para nomes de arquivo ❌

**Decisão**: 
- **Aceito para BETA**: Sanitização básica é suficiente
- **Backlog para PROD**: Implementar validação robusta e UUIDs

**Justificativa**: 
- Uploads são controlados em beta
- Sanitização básica previne ataques simples
- Melhorias podem ser feitas antes de produção pública

---

## 🟡 Vulnerabilidades Médias

### MED-001: CSP Permissiva ⚠️ ACEITO

**Status**: ⚠️ Parcialmente implementado  
**Data**: Janeiro 2025

**Implementação Atual**:
- CSP implementado ✅
- Permite `unsafe-inline` e `unsafe-eval` ⚠️
- Não usa nonces ❌

**Decisão**: 
- **Aceito para BETA**: CSP básico é suficiente
- **Backlog para PROD**: Remover unsafe-* e usar nonces

**Justificativa**: 
- HTMX requer inline scripts em alguns casos
- Não é crítico para ambiente controlado
- Pode ser melhorado antes de produção

---

### MED-003: Exposição de Versão ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito**: Exposição de versão não é crítica
- **Backlog**: Ocultar em produção se necessário

**Justificativa**: 
- Versão não expõe informações sensíveis
- Útil para debugging e suporte
- Pode ser ocultada facilmente se necessário

---

### MED-010: Validação MIME Type ⚠️ ACEITO

**Status**: ⚠️ Parcialmente implementado  
**Data**: Janeiro 2025

**Implementação Atual**:
- Valida magic bytes ✅
- Valida extensão ✅
- Não valida Content-Type ❌

**Decisão**: 
- **Aceito para BETA**: Validação de magic bytes é suficiente
- **Backlog para PROD**: Adicionar validação de Content-Type

**Justificativa**: 
- Magic bytes são mais confiáveis que Content-Type
- Content-Type pode ser facilmente falsificado
- Validação atual é robusta

---

### MED-011: Versões Fixas ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito para BETA**: Versões flexíveis facilitam desenvolvimento
- **Backlog para PROD**: Fixar versões antes de produção

**Justificativa**: 
- Ambiente controlado permite flexibilidade
- Facilita atualizações de segurança
- Fixar versões antes de produção pública

---

### MED-012: Verificação de Dependências ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito para BETA**: Verificação manual é suficiente
- **Backlog para PROD**: Implementar pip-audit no CI/CD

**Justificativa**: 
- Ambiente controlado permite verificação manual
- CI/CD será implementado antes de produção
- pip-audit pode ser adicionado facilmente

---

## 🟢 Vulnerabilidades Baixas

### LOW-002: Compression ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito**: Compression não é crítica
- **Backlog**: Implementar se necessário para performance

**Justificativa**: 
- Nginx pode fazer compression (se configurado)
- Não é crítico para segurança
- Pode ser implementado facilmente

---

### LOW-003: Cache Headers ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito**: Cache headers não são críticos
- **Backlog**: Implementar para otimização

**Justificativa**: 
- Não afeta segurança diretamente
- Pode ser implementado no Nginx
- Não é bloqueador

---

### LOW-004: Logs Estruturados ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito para BETA**: Logs texto são suficientes
- **Backlog para PROD**: Implementar JSON estruturado

**Justificativa**: 
- Logs texto são legíveis e suficientes para beta
- JSON estruturado facilita análise em produção
- Pode ser implementado facilmente

---

### LOW-006: Monitoring e Alerting ⚠️ ACEITO

**Status**: ❌ Não implementado  
**Data**: Janeiro 2025

**Decisão**: 
- **Aceito para BETA**: Monitoramento básico é suficiente
- **Backlog para PROD**: Implementar Prometheus + Grafana + Sentry

**Justificativa**: 
- Ambiente controlado não requer monitoramento avançado
- Alertas básicos podem ser configurados manualmente
- Stack completa será implementada antes de produção

---

## 📊 Resumo

### ✅ Resolvido: 10/30
- Todas as vulnerabilidades críticas
- Maioria das vulnerabilidades altas
- Algumas vulnerabilidades médias

### ⚠️ Aceito: 15/30
- Vulnerabilidades não críticas para beta
- Melhorias planejadas para produção
- Riscos aceitos com justificativa

### 📝 Backlog: 5/30
- Melhorias de performance
- Otimizações de segurança
- Features avançadas

---

## 🎯 Próximos Passos

### Antes de Produção Pública

1. Implementar validação de custo IA (HIGH-003)
2. Implementar validação robusta de uploads (HIGH-008)
3. Remover unsafe-* do CSP (MED-001)
4. Fixar versões de dependências (MED-011)
5. Implementar logs estruturados (LOW-004)
6. Configurar monitoramento completo (LOW-006)

---

**Última atualização**: Janeiro 2025
