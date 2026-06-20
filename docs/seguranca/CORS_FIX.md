# 🔧 Correção de CORS - BHub Backend

## Problema

O frontend rodando em `http://192.168.68.108:3000` estava sendo bloqueado pelo CORS ao tentar acessar o backend em `http://localhost:8000`.

## Solução Implementada

O backend agora permite automaticamente **qualquer origem local** em modo de desenvolvimento, incluindo:
- `localhost` ou `127.0.0.1`
- IPs de rede local privada:
  - `192.168.x.x` (ex: `192.168.68.108`)
  - `10.x.x.x`
  - `172.16-31.x.x`

## Como Funciona

### Modo Desenvolvimento

Quando `ENVIRONMENT=development` (padrão), o backend aceita qualquer origem local usando regex:

```python
allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+):\d+$"
```

### Modo Produção

Em produção, apenas origens explicitamente permitidas em `ALLOWED_ORIGINS` são aceitas.

## Verificar Configuração

Certifique-se de que o ambiente está configurado como desenvolvimento:

```bash
# No arquivo .env ou variáveis de ambiente
ENVIRONMENT=development
# ou
DEBUG=true
```

## Testar

1. Reinicie o servidor backend:
```bash
cd bhub-backend-python
uvicorn app.main:app --reload
```

2. Acesse o frontend em qualquer IP local:
   - `http://localhost:3000`
   - `http://192.168.68.108:3000`
   - `http://127.0.0.1:3000`

3. Verifique se as requisições funcionam sem erros de CORS.

## Troubleshooting

### Se ainda houver erro de CORS:

1. **Verifique o ambiente:**
   ```python
   # No Python console
   from app.config import settings
   print(settings.environment)  # Deve ser "development"
   print(settings.is_development)  # Deve ser True
   ```

2. **Verifique os logs do backend:**
   - Deve aparecer que está em modo desenvolvimento
   - Verifique se o middleware CORS está sendo aplicado

3. **Teste manualmente:**
   ```bash
   curl -H "Origin: http://192.168.68.108:3000" \
        -H "Access-Control-Request-Method: GET" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS \
        http://localhost:8000/api/v1/feeds \
        -v
   ```
   
   Deve retornar headers `Access-Control-Allow-Origin` e `Access-Control-Allow-Credentials`.

## Segurança

⚠️ **Importante**: Esta configuração é apenas para desenvolvimento. Em produção, sempre especifique origens exatas em `ALLOWED_ORIGINS`.

---

**Última atualização**: Dezembro 2024

