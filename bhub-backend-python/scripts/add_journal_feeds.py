
import asyncio
from app.database import get_session_context
from app.models import Feed, FeedType, SyncFrequency

JOURNAL_FEEDS = [
    # Portuguese
    {
        "name": "Revista Perspectivas",
        "journal_name": "Revista Perspectivas em Análise do Comportamento",
        "feed_url": "https://revistaperspectivas.org/perspectivas/feed",
        "website_url": "https://revistaperspectivas.org",
        "feed_type": FeedType.RSS
    },
    {
        "name": "Revista ESPECTRO",
        "journal_name": "Revista ESPECTRO",
        "feed_url": "https://espectro.ufscar.br/index.php/1979/gateway/plugin/WebFeedGatewayPlugin/rss2",
        "website_url": "https://espectro.ufscar.br",
        "feed_type": FeedType.RSS
    },
    {
        "name": "Boletim Contexto",
        "journal_name": "Boletim Contexto",
        "feed_url": "https://boletimcontexto.wordpress.com/feed",
        "website_url": "https://boletimcontexto.wordpress.com",
        "feed_type": FeedType.RSS
    },
    # English
    {
        "name": "JABA",
        "journal_name": "Journal of Applied Behavior Analysis",
        "feed_url": "https://onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1938-3703",
        "website_url": "https://onlinelibrary.wiley.com/journal/19383703",
        "feed_type": FeedType.RSS
    },
    {
        "name": "JEAB",
        "journal_name": "Journal of the Experimental Analysis of Behavior",
        "feed_url": "https://onlinelibrary.wiley.com/rss/journal/10.1002/(ISSN)1938-3711",
        "website_url": "https://onlinelibrary.wiley.com/journal/19383711",
        "feed_type": FeedType.RSS
    },
    {
        "name": "JOBM",
        "journal_name": "Journal of Organizational Behavior Management",
        "feed_url": "https://www.tandfonline.com/rss/journal/WORG20",
        "website_url": "https://www.tandfonline.com/journals/worg20",
        "feed_type": FeedType.RSS
    },
    {
        "name": "BAP",
        "journal_name": "Behavior Analysis in Practice",
        "feed_url": "https://link.springer.com/search.rss?facet-journal-id=40617&facet-content-type=Article",
        "website_url": "https://link.springer.com/journal/40617",
        "feed_type": FeedType.RSS
    },
    {
        "name": "Perspectives on Behavior Science",
        "journal_name": "Perspectives on Behavior Science",
        "feed_url": "https://link.springer.com/search.rss?facet-journal-id=40614&facet-content-type=Article",
        "website_url": "https://link.springer.com/journal/40614",
        "feed_type": FeedType.RSS
    },
    {
        "name": "The Analysis of Verbal Behavior",
        "journal_name": "The Analysis of Verbal Behavior",
        "feed_url": "https://link.springer.com/search.rss?facet-journal-id=40616&facet-content-type=Article",
        "website_url": "https://link.springer.com/journal/40616",
        "feed_type": FeedType.RSS
    },
    {
        "name": "Behavior and Social Issues",
        "journal_name": "Behavior and Social Issues",
        "feed_url": "https://link.springer.com/search.rss?facet-journal-id=42822&facet-content-type=Article",
        "website_url": "https://link.springer.com/journal/42822",
        "feed_type": FeedType.RSS
    },
    {
        "name": "OBM Network News",
        "journal_name": "OBM Network News",
        "feed_url": "https://www.obmnetwork.com/news/news_rss.asp",
        "website_url": "https://www.obmnetwork.com/news/",
        "feed_type": FeedType.RSS
    }
]

async def add_feeds():
    async with get_session_context() as session:
        count = 0
        for feed_data in JOURNAL_FEEDS:
            # Check if exists
            from sqlalchemy import select
            result = await session.execute(
                select(Feed).where(Feed.feed_url == feed_data["feed_url"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                feed = Feed(
                    name=feed_data["name"],
                    journal_name=feed_data["journal_name"],
                    feed_url=feed_data["feed_url"],
                    website_url=feed_data["website_url"],
                    feed_type=feed_data["feed_type"],
                    sync_frequency=SyncFrequency.DAILY
                )
                session.add(feed)
                count += 1
                print(f"Adding feed: {feed_data['name']}")
            else:
                # Update journal_name if missing (important for classification)
                if not existing.journal_name:
                    existing.journal_name = feed_data["journal_name"]
                    session.add(existing)
                    print(f"Updated journal_name for: {feed_data['name']}")

        await session.commit()
        print(f"Successfully processed {len(JOURNAL_FEEDS)} feeds. Added {count} new feeds.")

if __name__ == "__main__":
    asyncio.run(add_feeds())
