# Correções de Vulnerabilidades Críticas - Implementadas

Este documento descreve as correções implementadas para as 3 vulnerabilidades críticas identificadas na auditoria de segurança.

## ✅ CRIT-001: Rate Limiting Implementado

### Mudanças Implementadas

1. **Criado módulo de rate limiting** (`app/core/rate_limiting.py`):
   - Função `get_user_id_for_rate_limit()` que identifica usuários por token JWT ou IP
   - Suporte para rate limiting baseado em usuário autenticado

2. **Aplicado rate limiting nas rotas críticas**:
   - **Rotas de IA** (`/api/v1/ai/classify` e `/api/v1/ai/translate`): **10 requisições/minuto**
   - **Rotas de artigos** (`/api/v1/articles`): **100 requisições/minuto**
   - **Endpoint de cron** (`/api/v1/cron/sync`): **3 requisições/hora** (muito restritivo)

### Arquivos Modificados
- `app/core/rate_limiting.py` (novo)
- `app/api/v1/ai.py`
- `app/api/v1/articles.py`
- `app/main.py`

### Próximos Passos Recomendados
- Aplicar rate limiting em todas as outras rotas da API
- Configurar limites diferenciados por tipo de usuário (admin vs. público)
- Implementar rate limiting no nível do nginx (já configurado, verificar se está ativo)

---

## ✅ CRIT-002: Sanitização FTS5 Corrigida

### Mudanças Implementadas

1. **Melhorada função `_sanitize_query()`** em `app/services/search_service.py`:
   - **Whitelist approach**: Apenas permite caracteres alfanuméricos, espaços e acentos Unicode
   - **Remoção de palavras reservadas**: Filtra palavras reservadas do FTS5 (`AND`, `OR`, `NOT`, `MATCH`, `NEAR`, `rebuild`, `DELETE`)
   - **Limitação de termos**: Máximo de 10 termos por query
   - **Validação de tamanho**: Termos devem ter entre 2 e 50 caracteres
   - **Escape adequado**: Usa aspas duplas do FTS5 para tornar termos literais
   - **Limitação de tamanho total**: Query limitada a 200 caracteres

### Código Anterior (Vulnerável)
```python
def _sanitize_query(self, query: str) -> str:
    sanitized = re.sub(r'[*"\'():\-]', " ", query)
    # ... sem validação adequada
```

### Código Novo (Seguro)
```python
def _sanitize_query(self, query: str) -> str:
    # Limitar tamanho máximo
    if len(query) > 200:
        query = query[:200]
    
    # Whitelist approach: apenas caracteres seguros
    sanitized = re.sub(r'[^a-zA-Z0-9\s\u00C0-\u017F]', '', query)
    
    # Remover palavras reservadas do FTS5
    fts5_reserved = ['AND', 'OR', 'NOT', 'MATCH', 'NEAR', 'rebuild', 'DELETE']
    # ... validação rigorosa
```

### Arquivos Modificados
- `app/services/search_service.py`

### Testes Recomendados
- Testar queries com caracteres especiais
- Testar tentativas de injeção SQL
- Testar palavras reservadas do FTS5
- Testar queries muito longas

---

## ✅ CRIT-003: Tokens JWT com HttpOnly Cookies

### Mudanças Implementadas

1. **Criado middleware de cookies** (`app/core/auth_cookie_middleware.py`):
   - Intercepta respostas de login e adiciona cookie HttpOnly
   - Remove cookie em logout
   - Mantém compatibilidade com Bearer tokens (header Authorization)

2. **Reduzida expiração de tokens**:
   - **Access tokens**: Reduzido de 24 horas para **15 minutos**
   - Configuração em `app/config.py`

3. **Configuração de cookies seguros**:
   - `HttpOnly=True`: Previne acesso via JavaScript (proteção contra XSS)
   - `Secure=True` (em produção): Apenas HTTPS
   - `SameSite=Strict`: Previne CSRF
   - `Path=/`: Disponível em toda a aplicação

### Arquivos Criados/Modificados
- `app/core/auth_cookie_middleware.py` (novo)
- `app/core/cookie_transport.py` (criado mas não usado - mantido para referência futura)
- `app/main.py` (middleware adicionado)
- `app/config.py` (expiração reduzida)

### Compatibilidade
- **Frontend atual**: Continua funcionando com Bearer tokens no header
- **Futuro**: Frontend pode migrar para usar cookies automaticamente
- **Ambos funcionam**: Sistema aceita tokens de cookies OU headers

### Próximos Passos Recomendados
1. **Migrar frontend para usar cookies**:
   - Remover armazenamento manual de tokens no localStorage/sessionStorage
   - Configurar axios/fetch para enviar cookies automaticamente
   - Remover código que adiciona `Authorization: Bearer` manualmente

2. **Implementar refresh tokens**:
   - Criar endpoint `/api/v1/auth/refresh`
   - Implementar rotação de refresh tokens
   - Adicionar blacklist de tokens revogados (Redis)

3. **Adicionar revogação de tokens**:
   - Endpoint para revogar tokens ativos
   - Implementar blacklist em Redis ou banco de dados

---

## Resumo das Mudanças

### Segurança Melhorada
- ✅ Rate limiting ativo em rotas críticas
- ✅ Prevenção de SQL injection em queries FTS5
- ✅ Tokens JWT mais seguros (HttpOnly cookies + expiração curta)

### Compatibilidade Mantida
- ✅ Frontend atual continua funcionando
- ✅ Bearer tokens ainda são aceitos (compatibilidade)
- ✅ Cookies adicionados automaticamente em login

### Configuração
- ✅ Rate limits configuráveis via `app/config.py`
- ✅ Expiração de tokens configurável
- ✅ Cookies seguros apenas em produção

---

## Testes Necessários

### Rate Limiting
```bash
# Testar limite de 10/minuto em rotas de IA
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/v1/ai/translate \
    -H "Content-Type: application/json" \
    -d '{"text": "test", "target_lang": "pt"}'
done
# Deve retornar 429 após 10 requisições
```

### Sanitização FTS5
```bash
# Testar query maliciosa
curl "http://localhost:8000/api/v1/articles?search=rebuild%20OR%201=1"
# Deve sanitizar e não executar SQL
```

### Cookies HttpOnly
```bash
# Fazer login e verificar cookie
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=senha" \
  -c cookies.txt -v
# Deve retornar cookie HttpOnly
```

---

## Notas Importantes

1. **Em desenvolvimento**: Cookies `Secure=False` para permitir HTTP local
2. **Em produção**: Cookies `Secure=True` (apenas HTTPS)
3. **Rate limiting**: Baseado em IP ou user_id do JWT
4. **Compatibilidade**: Sistema aceita tokens de cookies OU headers (transição suave)

---

## Próximas Correções Prioritárias

Após estas correções críticas, recomenda-se implementar as vulnerabilidades **ALTAS**:

1. **HIGH-001**: Validação robusta de uploads de PDF
2. **HIGH-002**: Restringir headers CORS permitidos
3. **HIGH-003**: Rate limiting específico para rotas de IA (já feito parcialmente)
4. **HIGH-004**: Sanitização de logs
5. **HIGH-005**: Validação de URLs de scraping (prevenir SSRF)

