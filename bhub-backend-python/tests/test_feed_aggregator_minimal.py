import pytest

from app.services.feed_aggregator import FeedAggregatorService


class FakeResult:
    def scalar_one_or_none(self):
        return None


class FakeDB:
    async def execute(self, *_args, **_kwargs):
        return FakeResult()


@pytest.mark.asyncio
async def test_sync_feed_not_found():
    service = FeedAggregatorService(db=FakeDB())
    result = await service.sync_feed(feed_id=123)
    assert result.success is False
    assert "Feed não encontrado" in (result.errors or [])
