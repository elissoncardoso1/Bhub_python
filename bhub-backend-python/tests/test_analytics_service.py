"""
Testes do AnalyticsService.
"""

from datetime import datetime, timedelta

import pytest

from app.models.analytics import AnalyticsSession
from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_get_traffic_stats_counts_anonymous_and_authenticated_visitors(db_session):
    now = datetime.utcnow()

    db_session.add_all(
        [
            # Mesmo usuario autenticado em duas sessoes -> conta 1 visitante autenticado.
            AnalyticsSession(
                session_id="sess-user-1",
                user_id=10,
                started_at=now - timedelta(hours=1),
                last_activity=now - timedelta(minutes=30),
                duration_seconds=120,
            ),
            AnalyticsSession(
                session_id="sess-user-2",
                user_id=10,
                started_at=now - timedelta(hours=2),
                last_activity=now - timedelta(minutes=40),
                duration_seconds=60,
            ),
            # Dois anonimos em sessoes diferentes -> contam 2 visitantes anonimos.
            AnalyticsSession(
                session_id="sess-anon-1",
                user_id=None,
                started_at=now - timedelta(minutes=50),
                last_activity=now - timedelta(minutes=20),
                duration_seconds=30,
            ),
            AnalyticsSession(
                session_id="sess-anon-2",
                user_id=None,
                started_at=now - timedelta(minutes=10),
                last_activity=now - timedelta(minutes=2),
                duration_seconds=45,
            ),
        ]
    )
    await db_session.commit()

    stats = await AnalyticsService.get_traffic_stats(db_session, days=30)
    assert stats["unique_visitors"] == 3
