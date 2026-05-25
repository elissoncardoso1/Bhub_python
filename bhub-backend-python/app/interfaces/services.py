"""
Protocols dos serviços de aplicação.

Os contratos são estruturais: qualquer classe com os métodos compatíveis pode
ser injetada nas rotas ou substituída por stubs nos testes.
"""

from typing import Protocol, runtime_checkable

from app.schemas.article import ArticleResponse

CategorySlug = str


@runtime_checkable
class IClassificationService(Protocol):
    async def classify(self, text: str) -> tuple[CategorySlug, float]:
        """Retorna slug de categoria e confiança entre 0 e 1."""
        ...

    async def classify_batch(self, texts: list[str]) -> list[tuple[CategorySlug, float]]:
        """Classifica vários textos preservando a ordem de entrada."""
        ...

    async def classify_article(self, article_id: int) -> tuple[CategorySlug, float] | None:
        """Classifica e persiste a categoria principal de um artigo."""
        ...


@runtime_checkable
class ISearchService(Protocol):
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ArticleResponse]:
        ...

    async def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        ...

    async def search_fts5(self, query: str, limit: int = 20, offset: int = 0) -> list[int]:
        ...

    async def search_like_fallback(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: int | None = None,
    ) -> list[int]:
        ...


@runtime_checkable
class IFeedAggregator(Protocol):
    async def sync_feed(self, feed_id: int):
        ...

    async def sync_all_active_feeds(self):
        ...

    async def close(self) -> None:
        ...


@runtime_checkable
class IAIManager(Protocol):
    async def classify(self, text: str) -> tuple[CategorySlug, float] | tuple[CategorySlug, float, object]:
        ...

    async def translate(self, text: str, target_lang: str = "pt"):
        ...

    def get_status(self) -> dict:
        ...
