"""
Rate limiter global para a aplicação.
Separado de app.main para evitar importações circulares.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter global
limiter = Limiter(key_func=get_remote_address)
