"""
Configuração de templates Jinja2 para SSR/HTMX.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings

MONTHS_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _format_date(value: datetime | None, fmt: str = "%d/%m/%Y") -> str:
    if not value:
        return ""
    return value.strftime(fmt)


def _format_date_br(value: datetime | None, mode: str = "full") -> str:
    """
    Formata data no estilo brasileiro.
    mode="full": "DD de Mês de AAAA" (ex: 29 de Dezembro de 2025)
    mode="month_year": "Mês de AAAA" (ex: Dezembro de 2025)
    """
    if not value:
        return ""

    month_name = MONTHS_PT.get(value.month, "")

    if mode == "month_year":
        return f"{month_name} de {value.year}"

    # Default is full date
    return f"{value.day} de {month_name} de {value.year}"


def _ellipsis(text: str | None, max_len: int = 220) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _format_float(value: float | None, decimals: int = 1) -> str:
    """Formata um float com número específico de decimais."""
    if value is None:
        return "0.0"
    return f"{value:.{decimals}f}"


def _format_percent(value: float | None) -> str:
    """Formata um float como percentual (0.0-1.0 -> 0-100%)."""
    if value is None:
        return "0"
    return str(int(round(value * 100)))


@lru_cache
def get_templates() -> Jinja2Templates:
    templates_dir = Path(settings.base_dir) / "app" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    templates.env.filters["date_fmt"] = _format_date
    templates.env.filters["date_fmt_br"] = _format_date_br
    templates.env.filters["ellipsis"] = _ellipsis
    templates.env.filters["format_float"] = _format_float
    templates.env.filters["format_percent"] = _format_percent
    templates.env.globals["settings"] = settings
    templates.env.globals["now"] = datetime.utcnow

    from app.utils.icons import icons
    templates.env.globals["icon"] = icons.get

    return templates
