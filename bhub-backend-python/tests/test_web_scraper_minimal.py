import pytest

from app.services.web_scraper import WebScrapingService


def test_validate_url_rejects_scheme():
    service = WebScrapingService()
    with pytest.raises(ValueError):
        service._validate_url("ftp://example.com")


def test_validate_url_rejects_localhost():
    service = WebScrapingService()
    with pytest.raises(ValueError):
        service._validate_url("http://localhost/test")


def test_validate_url_allows_public_ip():
    service = WebScrapingService()
    service._validate_url("http://8.8.8.8/path")


def test_validate_url_rejects_dangerous_path():
    service = WebScrapingService()
    with pytest.raises(ValueError):
        service._validate_url("https://example.com/../secret")
