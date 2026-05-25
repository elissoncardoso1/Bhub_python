"""
Schemas de autor.
"""



from app.schemas.common import BaseSchema


class AuthorBase(BaseSchema):
    """Campos base de autor."""
    name: str
    orcid: str | None = None
    affiliation: str | None = None


class AuthorResponse(AuthorBase):
    """Resposta de autor."""
    id: int
    role: str | None = "author"


class AuthorWithStats(AuthorResponse):
    """Autor com estatísticas."""
    article_count: int = 0
