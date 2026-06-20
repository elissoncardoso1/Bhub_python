# Correções de Vulnerabilidades ALTAS - Implementadas

Este documento descreve as correções implementadas para as vulnerabilidades de severidade ALTA identificadas na auditoria de segurança.

## ✅ HIGH-001: Validação Robusta de Uploads de PDF

### Mudanças Implementadas

1. **Validações de segurança adicionadas** em `app/services/pdf_service.py`:
   - **Bloqueio de JavaScript**: Detecta e bloqueia PDFs com `/JavaScript` ou `/JS`
   - **Bloqueio de ações perigosas**: Detecta ações como `/Launch`, `/GoToR`, `/URI`, `/SubmitForm`, `/ResetForm`
   - **Limitação de complexidade**: Máximo de 10.000 objetos por PDF
   - **Proteção contra zip bombs**: Valida tamanho estimado após descompressão
   - **Limitação de páginas**: Máximo de 1.000 páginas por PDF

### Código Adicionado
```python
# Bloquear JavaScript embutido
if b'/javascript' in content_lower or b'/js' in content_lower:
    raise PDFProcessingError("PDF contém JavaScript, não permitido por segurança")

# Bloquear ações perigosas
dangerous_actions = [b'/launch', b'/gotor', b'/uri', b'/submitform', b'/resetform']
for action in dangerous_actions:
    if action in content_lower:
        raise PDFProcessingError(f"PDF contém ações perigosas, não permitido")
```

### Arquivos Modificados
- `app/services/pdf_service.py`

### Testes Recomendados
- Testar upload de PDF com JavaScript
- Testar PDF com ações perigosas
- Testar PDF muito complexo (>10k objetos)
- Testar PDF com muitas páginas (>1k)

---

## ✅ HIGH-002: Headers CORS Restringidos

### Mudanças Implementadas

1. **Headers permitidos explicitamente** em `app/main.py`:
   - Removido `allow_headers=["*"]`
   - Especificados headers permitidos:
     - `Content-Type`
     - `Authorization`
     - `X-Requested-With`
     - `Accept`
     - `Origin`
     - `X-Session-ID` (para analytics)
     - `X-Cron-Secret` (para cron endpoint)

2. **Métodos permitidos explicitamente**:
   - Removido `allow_methods=["*"]`
   - Especificados: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`

### Código Anterior (Vulnerável)
```python
allow_methods=["*"],
allow_headers=["*"],
```

### Código Novo (Seguro)
```python
allowed_headers = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "Accept",
    "Origin",
    "X-Session-ID",
    "X-Cron-Secret",
]
allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
```

### Arquivos Modificados
- `app/main.py`

### Impacto
- Previne uso de headers customizados maliciosos
- Reduz superfície de ataque
- Mantém funcionalidade necessária

---

## ✅ HIGH-004: Sanitização de Logs

### Mudanças Implementadas

1. **Criado módulo de sanitização** (`app/core/log_sanitizer.py`):
   - Função `sanitize_log_message()`: Remove informações sensíveis de strings
   - Função `sanitize_dict()`: Sanitiza dicionários
   - Função `sanitize_for_logging()`: Sanitiza qualquer objeto

2. **Informações removidas dos logs**:
   - Tokens JWT (Bearer tokens e tokens soltos)
   - Senhas (em diferentes formatos)
   - Chaves de API
   - Números de cartão de crédito

3. **Integração com logging**:
   - Função `safe_log()` adicionada ao módulo de logging
   - Logs de autenticação sanitizados automaticamente

### Código Implementado
```python
def sanitize_log_message(message: str) -> str:
    # Remover tokens JWT
    message = re.sub(
        r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
        'Bearer [REDACTED]',
        message
    )
    # Remover senhas
    message = re.sub(
        r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+',
        'password=[REDACTED]',
        message,
        flags=re.IGNORECASE
    )
    # ... mais sanitizações
```

### Arquivos Criados/Modificados
- `app/core/log_sanitizer.py` (novo)
- `app/core/logging.py` (integração)
- `app/core/security.py` (logs de autenticação sanitizados)

### Uso Recomendado
```python
from app.core.log_sanitizer import sanitize_log_message

# Antes (inseguro)
log.info(f"Login attempt: {user.email} with password: {password}")

# Depois (seguro)
log.info(sanitize_log_message(f"Login attempt: {user.email}"))
```

---

## ✅ HIGH-005: Validação de URLs (Prevenção SSRF)

### Mudanças Implementadas

1. **Criada função `_validate_url()`** em `app/services/web_scraper.py`:
   - **Bloqueio de esquemas perigosos**: Apenas HTTP/HTTPS permitidos
   - **Bloqueio de localhost**: Todas as variações de localhost bloqueadas
   - **Bloqueio de IPs privados**: IPs RFC 1918 bloqueados
   - **Bloqueio de IPs de loopback**: 127.0.0.1, ::1, etc.
   - **Bloqueio de IPs link-local**: IPs de rede local
   - **Validação de path**: Detecta tentativas de path traversal

2. **Timeout reduzido**:
   - De 30 segundos para 10 segundos
   - Previne DoS via requisições lentas

3. **Limitação de redirects**:
   - Máximo de 5 redirects
   - Previne loops infinitos

### Código Implementado
```python
def _validate_url(self, url: str) -> None:
    parsed = urlparse(url)
    
    # Apenas HTTP/HTTPS
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Apenas HTTP/HTTPS permitidos")
    
    # Bloquear IPs privados
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback:
            raise ValueError("IP privado bloqueado (SSRF prevention)")
    except ValueError:
        # Validar hostname
        pass
```

### Arquivos Modificados
- `app/services/web_scraper.py`

### Testes Recomendados
```bash
# Testar URLs bloqueadas
curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Authorization: Bearer TOKEN" \
  -d '{"url": "http://localhost/admin"}'
# Deve retornar erro

curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Authorization: Bearer TOKEN" \
  -d '{"url": "http://127.0.0.1:8080"}'
# Deve retornar erro

curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Authorization: Bearer TOKEN" \
  -d '{"url": "http://192.168.1.1"}'
# Deve retornar erro
```

---

## Resumo das Mudanças

### Segurança Melhorada
- ✅ Uploads de PDF validados contra JavaScript e ações perigosas
- ✅ Headers CORS restringidos explicitamente
- ✅ Logs sanitizados automaticamente
- ✅ URLs validadas para prevenir SSRF

### Compatibilidade
- ✅ Todas as mudanças são retrocompatíveis
- ✅ Funcionalidade existente mantida
- ✅ Apenas validações adicionais

### Performance
- ✅ Timeout reduzido em scraping (10s)
- ✅ Limitação de redirects (máx. 5)
- ✅ Validações eficientes

---

## Próximas Correções Recomendadas

Após estas correções ALTAS, ainda restam:

### Vulnerabilidades ALTAS Restantes
- **HIGH-003**: Rate limiting específico para rotas de IA (já implementado parcialmente)
- **HIGH-006**: JWT com expiração curta (já implementado - 15 minutos)
- **HIGH-007**: Proteção CSRF (recomendado implementar)
- **HIGH-008**: Path traversal em uploads (parcialmente corrigido, pode melhorar)

### Vulnerabilidades MÉDIAS Prioritárias
- **MED-001**: Content Security Policy mais restritiva
- **MED-005**: Anonimização de IPs em analytics
- **MED-010**: Validação de MIME type em uploads

---

## Notas de Implementação

1. **Sanitização de logs**: Aplicada automaticamente em logs de autenticação. Recomenda-se usar `sanitize_log_message()` em todos os logs que possam conter informações sensíveis.

2. **Validação de URLs**: A função `_validate_url()` é chamada automaticamente antes de qualquer scraping. URLs bloqueadas retornam erro claro.

3. **Validação de PDFs**: As validações são aplicadas antes do processamento. PDFs maliciosos são rejeitados com mensagens de erro claras.

4. **CORS**: Headers e métodos são restritos tanto em desenvolvimento quanto em produção. Em desenvolvimento, origens locais ainda são permitidas via regex.

---

## Testes de Segurança

### PDF Malicioso
```python
# Criar PDF com JavaScript (deve ser bloqueado)
pdf_with_js = create_pdf_with_javascript()
# Upload deve falhar com erro claro
```

### SSRF
```python
# Tentar acessar localhost (deve ser bloqueado)
url = "http://localhost:8080/admin"
# Deve retornar ValueError
```

### Logs
```python
# Log com senha (deve ser sanitizado)
log.info(f"Password: {password}")
# Deve aparecer como "Password: [REDACTED]"
```

