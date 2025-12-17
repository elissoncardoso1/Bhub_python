"""
Utilitários para anonimização de endereços IP (LGPD/GDPR compliance).
"""

import ipaddress
from typing import Optional


def anonymize_ip(ip_address: Optional[str]) -> Optional[str]:
    """
    Anonimiza um endereço IP removendo o último octeto (IPv4) ou últimos 64 bits (IPv6).
    
    Isso mantém informações geográficas gerais enquanto protege a privacidade
    do usuário individual, em conformidade com LGPD/GDPR.
    
    Args:
        ip_address: Endereço IP a ser anonimizado (ex: "192.168.1.100")
    
    Returns:
        IP anonimizado (ex: "192.168.1.0") ou None se IP inválido
    
    Examples:
        >>> anonymize_ip("192.168.1.100")
        "192.168.1.0"
        >>> anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        "2001:0db8:85a3:0000::"
        >>> anonymize_ip(None)
        None
        >>> anonymize_ip("invalid")
        None
    """
    if not ip_address:
        return None
    
    try:
        # Tentar parsear como IPv4
        ip = ipaddress.IPv4Address(ip_address)
        # Zerar último octeto
        parts = str(ip).split(".")
        parts[-1] = "0"
        return ".".join(parts)
    except ValueError:
        try:
            # Tentar parsear como IPv6
            ip = ipaddress.IPv6Address(ip_address)
            # Zerar últimos 64 bits (últimos 4 grupos)
            parts = str(ip).split(":")
            # IPv6 pode ter :: para zeros, normalizar
            if "::" in str(ip):
                # Simplificar: retornar primeiros 4 grupos + ::
                parts = str(ip).split("::")[0].split(":")
                if len(parts) < 4:
                    parts = parts + ["0"] * (4 - len(parts))
                return ":".join(parts[:4]) + "::"
            else:
                # Zerar últimos 4 grupos
                parts = str(ip).split(":")
                parts[-4:] = ["0", "0", "0", "0"]
                return ":".join(parts)
        except ValueError:
            # IP inválido
            return None


def should_anonymize_ip() -> bool:
    """
    Verifica se IPs devem ser anonimizados baseado em configuração.
    
    Por padrão, sempre anonimizar em produção para compliance LGPD/GDPR.
    """
    from app.config import settings
    
    # Sempre anonimizar em produção
    if settings.is_production:
        return True
    
    # Em desenvolvimento, pode ser configurável via env
    # Por padrão, anonimizar também
    return True

