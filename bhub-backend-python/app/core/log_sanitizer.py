"""
Utilitários para sanitização de logs.
Remove informações sensíveis antes de registrar em logs.
"""

import re
from typing import Any


def sanitize_log_message(message: str) -> str:
    """
    Remove informações sensíveis de mensagens de log.
    
    Remove:
    - Tokens JWT (Bearer tokens)
    - Senhas em diferentes formatos
    - Chaves de API
    - Números de cartão de crédito (parcial)
    """
    if not isinstance(message, str):
        message = str(message)
    
    # Remover tokens JWT (Bearer tokens)
    # Formato: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    message = re.sub(
        r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
        'Bearer [REDACTED]',
        message
    )
    
    # Remover tokens JWT sem "Bearer" prefix
    message = re.sub(
        r'\beyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b',
        '[JWT_TOKEN_REDACTED]',
        message
    )
    
    # Remover senhas em diferentes formatos
    # password="senha" ou password: senha ou password=senha
    message = re.sub(
        r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+',
        'password=[REDACTED]',
        message,
        flags=re.IGNORECASE
    )
    
    # Remover chaves de API comuns
    api_key_patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+',
        r'apikey["\']?\s*[:=]\s*["\']?[^"\'\s]+',
        r'secret[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+',
        r'access[_-]?token["\']?\s*[:=]\s*["\']?[^"\'\s]+',
    ]
    for pattern in api_key_patterns:
        message = re.sub(
            pattern,
            '[API_KEY_REDACTED]',
            message,
            flags=re.IGNORECASE
        )
    
    # Remover possíveis números de cartão (parcial - apenas últimos 4 dígitos)
    # Formato: 1234-5678-9012-3456 ou 1234567890123456
    message = re.sub(
        r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        '[CARD_REDACTED]',
        message
    )
    
    return message


def sanitize_dict(data: dict) -> dict:
    """
    Sanitiza um dicionário removendo valores sensíveis.
    """
    sensitive_keys = [
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token',
        'api_key', 'apikey', 'secret_key',
        'authorization', 'auth',
        'credit_card', 'card_number',
        'ssn', 'cpf', 'cnpj',
    ]
    
    sanitized = {}
    for key, value in data.items():
        key_lower = str(key).lower()
        
        # Verificar se a chave é sensível
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, str):
            sanitized[key] = sanitize_log_message(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_for_logging(obj: Any) -> Any:
    """
    Sanitiza qualquer objeto para logging seguro.
    """
    if isinstance(obj, str):
        return sanitize_log_message(obj)
    elif isinstance(obj, dict):
        return sanitize_dict(obj)
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_logging(item) for item in obj]
    else:
        return obj

