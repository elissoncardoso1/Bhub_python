"""
Serviço de web scraping para extração de artigos.
"""

import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from selectolax.parser import HTMLParser
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import log
from app.models import SourceType


class WebScrapingService:
    """Serviço para scraping de artigos de páginas web."""

    # Headers para simular navegador
    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Seletores comuns para artigos científicos
    TITLE_SELECTORS = [
        "h1.article-title",
        "h1.title",
        "h1[itemprop='headline']",
        ".article-header h1",
        ".article__title",
        "article h1",
        ".content-header h1",
        "h1",
    ]

    ABSTRACT_SELECTORS = [
        ".abstract",
        "[class*='abstract']",
        "#abstract",
        ".article-abstract",
        ".summary",
        "[itemprop='description']",
        "section.abstract",
        ".ArticleAbstract",
    ]

    AUTHOR_SELECTORS = [
        ".author-name",
        ".authors a",
        "[rel='author']",
        ".article-author",
        "[itemprop='author']",
        ".contributor",
        ".author",
        "meta[name='author']",
        "meta[name='citation_author']",
    ]

    KEYWORDS_SELECTORS = [
        ".keywords",
        "[class*='keyword']",
        "meta[name='keywords']",
        "meta[name='citation_keywords']",
        ".article-keywords",
    ]

    DOI_SELECTORS = [
        "meta[name='citation_doi']",
        "meta[name='DC.identifier']",
        "[class*='doi']",
        "a[href*='doi.org']",
    ]

    DATE_SELECTORS = [
        "meta[name='citation_publication_date']",
        "meta[name='DC.date']",
        "meta[name='article:published_time']",
        "time[datetime]",
        "[itemprop='datePublished']",
        ".publication-date",
        ".date",
    ]

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=self.BROWSER_HEADERS,
        )

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def scrape_url(self, url: str) -> dict:
        """
        Extrai dados de artigo de uma URL.
        
        Returns:
            dict com dados do artigo
        """
        log.info(f"Iniciando scraping: {url}")

        # Validar URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("URL inválida")

        # Fazer requisição
        response = await self.client.get(url)
        response.raise_for_status()

        html = response.text
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Parse com BeautifulSoup para extração complexa
        soup = BeautifulSoup(html, "lxml")

        # Parse com selectolax para operações mais rápidas
        tree = HTMLParser(html)

        # Extrair dados
        data = {
            "title": self._extract_title(soup),
            "abstract": self._extract_abstract(soup),
            "authors": self._extract_authors(soup),
            "keywords": self._extract_keywords(soup),
            "doi": self._extract_doi(soup, url),
            "publication_date": self._extract_date(soup),
            "image_url": self._extract_image(soup, base_url),
            "original_url": url,
            "source_type": SourceType.SCRAPING,
            "language": self._detect_language(soup),
            "external_id": self._generate_external_id(url),
        }

        log.info(f"Scraping concluído: {data['title'][:50]}...")
        return data

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrai título do artigo."""
        # Tentar meta tags primeiro
        meta_title = soup.find("meta", {"name": "citation_title"})
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()

        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()

        # Tentar seletores
        for selector in self.TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 5:
                    return text

        # Fallback para tag title
        if soup.title:
            return soup.title.get_text(strip=True)

        return "Sem título"

    def _extract_abstract(self, soup: BeautifulSoup) -> str | None:
        """Extrai abstract do artigo."""
        # Tentar meta tags
        meta = soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            content = meta["content"].strip()
            if len(content) > 100:  # Abstract geralmente tem mais de 100 chars
                return content

        meta = soup.find("meta", {"name": "citation_abstract"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Tentar seletores
        for selector in self.ABSTRACT_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 50:
                    # Limitar tamanho
                    return text[:5000] if len(text) > 5000 else text

        return None

    def _extract_authors(self, soup: BeautifulSoup) -> list[str]:
        """Extrai lista de autores."""
        authors = []

        # Tentar meta tags
        meta_authors = soup.find_all("meta", {"name": "citation_author"})
        for meta in meta_authors:
            if meta.get("content"):
                authors.append(meta["content"].strip())

        if authors:
            return authors

        # Tentar seletores
        for selector in self.AUTHOR_SELECTORS:
            elements = soup.select(selector)
            for el in elements:
                if el.name == "meta":
                    text = el.get("content", "")
                else:
                    text = el.get_text(strip=True)

                if text and len(text) > 2:
                    # Dividir se houver múltiplos autores
                    if "," in text and len(text) > 50:
                        authors.extend([a.strip() for a in text.split(",")])
                    else:
                        authors.append(text)

            if authors:
                break

        # Limpar duplicatas
        seen = set()
        unique = []
        for a in authors:
            if a.lower() not in seen:
                unique.append(a)
                seen.add(a.lower())

        return unique[:20]  # Limitar a 20 autores

    def _extract_keywords(self, soup: BeautifulSoup) -> str | None:
        """Extrai keywords do artigo."""
        keywords = []

        # Tentar meta tags
        meta = soup.find("meta", {"name": "keywords"})
        if meta and meta.get("content"):
            keywords = [k.strip() for k in meta["content"].split(",")]

        if not keywords:
            meta_list = soup.find_all("meta", {"name": "citation_keywords"})
            for meta in meta_list:
                if meta.get("content"):
                    keywords.append(meta["content"].strip())

        # Tentar seletores
        if not keywords:
            for selector in self.KEYWORDS_SELECTORS:
                elements = soup.select(selector)
                for el in elements:
                    if el.name == "meta":
                        text = el.get("content", "")
                    else:
                        text = el.get_text(strip=True)

                    if text:
                        if "," in text:
                            keywords.extend([k.strip() for k in text.split(",")])
                        else:
                            keywords.append(text)

                if keywords:
                    break

        if keywords:
            unique = list(dict.fromkeys(keywords))
            return ", ".join(unique[:20])

        return None

    def _extract_doi(self, soup: BeautifulSoup, url: str) -> str | None:
        """Extrai DOI do artigo."""
        # Tentar meta tags
        meta = soup.find("meta", {"name": "citation_doi"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        meta = soup.find("meta", {"name": "DC.identifier"})
        if meta and meta.get("content"):
            content = meta["content"]
            if "10." in content:
                match = re.search(r"10\.\d{4,}/[^\s]+", content)
                if match:
                    return match.group(0)

        # Procurar link com DOI
        doi_link = soup.find("a", href=re.compile(r"doi\.org"))
        if doi_link:
            href = doi_link.get("href", "")
            match = re.search(r"10\.\d{4,}/[^\s]+", href)
            if match:
                return match.group(0)

        # Procurar na URL original
        match = re.search(r"10\.\d{4,}/[^\s]+", url)
        if match:
            return match.group(0)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Extrai data de publicação."""
        # Tentar meta tags
        for name in ["citation_publication_date", "DC.date", "article:published_time"]:
            meta = soup.find("meta", {"name": name}) or soup.find("meta", {"property": name})
            if meta and meta.get("content"):
                try:
                    return date_parser.parse(meta["content"])
                except Exception:
                    pass

        # Tentar elemento time
        time_el = soup.find("time", {"datetime": True})
        if time_el:
            try:
                return date_parser.parse(time_el["datetime"])
            except Exception:
                pass

        # Tentar seletores
        for selector in self.DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get("datetime") or element.get("content") or element.get_text(strip=True)
                if text:
                    try:
                        return date_parser.parse(text)
                    except Exception:
                        pass

        return None

    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> str | None:
        """Extrai imagem do artigo."""
        # Tentar og:image
        meta = soup.find("meta", {"property": "og:image"})
        if meta and meta.get("content"):
            img_url = meta["content"]
            if not img_url.startswith("http"):
                img_url = urljoin(base_url, img_url)
            return img_url

        # Tentar twitter:image
        meta = soup.find("meta", {"name": "twitter:image"})
        if meta and meta.get("content"):
            img_url = meta["content"]
            if not img_url.startswith("http"):
                img_url = urljoin(base_url, img_url)
            return img_url

        # Procurar imagem no artigo
        article = soup.find("article") or soup.find("main") or soup
        img = article.find("img", src=True)
        if img:
            img_url = img["src"]
            if not img_url.startswith("http"):
                img_url = urljoin(base_url, img_url)

            # Filtrar imagens muito pequenas ou de tracking
            if not any(x in img_url.lower() for x in ["pixel", "track", "beacon", "1x1"]):
                return img_url

        return None

    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detecta idioma do artigo."""
        # Tentar atributo lang
        html = soup.find("html")
        if html and html.get("lang"):
            return html["lang"][:2].lower()

        # Tentar meta tag
        meta = soup.find("meta", {"http-equiv": "content-language"})
        if meta and meta.get("content"):
            return meta["content"][:2].lower()

        meta = soup.find("meta", {"name": "language"})
        if meta and meta.get("content"):
            return meta["content"][:2].lower()

        return "en"

    def _generate_external_id(self, url: str) -> str:
        """Gera ID externo único para o artigo."""
        return f"scrape_{hashlib.md5(url.encode()).hexdigest()}"
