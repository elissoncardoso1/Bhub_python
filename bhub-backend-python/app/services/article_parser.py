"""
Serviço de parsing de artigos de feeds RSS/Atom.
"""

import hashlib
import html
import re
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser

from app.core.logging import log
from bs4 import BeautifulSoup


class ArticleParserService:
    """Serviço para parsing de entradas de feeds RSS/Atom."""

    def generate_external_id(self, entry: dict, feed_id: int) -> str:
        """Gera ID externo único para o artigo."""
        # Tentar usar guid/id do feed
        guid = entry.get("id") or entry.get("guid") or entry.get("link")

        if guid:
            return f"feed_{feed_id}_{hashlib.md5(guid.encode()).hexdigest()}"

        # Fallback: usar título + data
        title = entry.get("title", "")
        date = entry.get("published", entry.get("updated", ""))
        content = f"{title}_{date}"
        return f"feed_{feed_id}_{hashlib.md5(content.encode()).hexdigest()}"

    def parse_entry(self, entry: dict, journal_name: str | None = None) -> dict[str, Any]:
        """Extrai dados de uma entrada de feed."""
        return {
            "title": self._extract_title(entry, journal_name),
            "abstract": self._extract_abstract(entry),
            "url": self._extract_url(entry),
            "publication_date": self._extract_date(entry),
            "authors": self._extract_authors(entry),
            "keywords": self._extract_keywords(entry),
            "doi": self._extract_doi(entry),
            "journal": self._extract_journal(entry),
            "language": self._detect_language(entry),
            "image_url": self._extract_image(entry),
        }

    def _extract_title(self, entry: dict, journal_name: str | None = None) -> str:
        """Extrai título do artigo."""
        title = entry.get("title", "")
        if isinstance(title, dict):
            title = title.get("value", "") or title.get("content", "")

        # Limpar HTML
        title = re.sub(r"<[^>]+>", "", title)
        # Decodificar entidades HTML (e.g., &#8217; -> ')
        title = html.unescape(title)
        title = title.strip()

        # Remover prefixos comuns de RSS
        title = re.sub(r"^(Article:|Original Article:|Artigo:)\s*", "", title, flags=re.IGNORECASE)

        # Remover nome do journal se presente no título (sufixo comum em feeds)
        if journal_name and len(journal_name) > 3:
            # Padrões comuns: "Titulo - Journal", "Titulo | Journal", "Titulo [Journal]"
            patterns = [
                rf"\s+[-|–]\s+{re.escape(journal_name)}$",
                rf"\s+\[{re.escape(journal_name)}\]$",
                rf"\s+\({re.escape(journal_name)}\)$"
            ]
            for pattern in patterns:
                title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        return title or "Sem título"

    def _extract_abstract(self, entry: dict) -> str | None:
        """Extrai abstract/resumo do artigo."""
        # Tentar diferentes campos
        abstract = None

        # Campo summary
        if "summary" in entry:
            summary = entry["summary"]
            if isinstance(summary, dict):
                abstract = summary.get("value", "") or summary.get("content", "")
            else:
                abstract = summary

        # Campo content
        if not abstract and "content" in entry:
            content = entry["content"]
            if isinstance(content, list) and content:
                abstract = content[0].get("value", "")
            elif isinstance(content, dict):
                abstract = content.get("value", "")

        # Campo description
        if not abstract:
            abstract = entry.get("description", "")

        if abstract:
            # Limpar HTML mantendo parágrafos
            abstract = re.sub(r"<br\s*/?>", "\n", abstract)
            abstract = re.sub(r"</p>", "\n", abstract)
            abstract = re.sub(r"<[^>]+>", "", abstract)
            # Decodificar entidades HTML (e.g., &#8230; -> …, &#8216; -> ')
            abstract = html.unescape(abstract)
            
            # Remover boilerplate de WordPress "Tempo de Leitura: X minutos"
            abstract = re.sub(r"^Tempo de Leitura:\s*<?[\s\d]+\s*minutos?\s*", "", abstract, flags=re.IGNORECASE)
            
            # Remover rodapé "O post ... apareceu primeiro em ..."
            abstract = re.sub(r"\s*O post\s+.+?\s+apareceu primeiro em\s+.+\.\s*$", "", abstract, flags=re.IGNORECASE)
            
            abstract = abstract.strip()

            # Limitar tamanho
            if len(abstract) > 5000:
                abstract = abstract[:5000] + "..."

        return abstract if abstract else None

    def _extract_url(self, entry: dict) -> str | None:
        """Extrai URL do artigo."""
        # Tentar campo link
        link = entry.get("link")
        if isinstance(link, str):
            return link
        if isinstance(link, dict):
            return link.get("href")

        # Tentar lista de links
        links = entry.get("links", [])
        for l in links:
            if isinstance(l, dict):
                if l.get("rel") == "alternate" or l.get("type") == "text/html":
                    return l.get("href")
                if "href" in l:
                    return l["href"]

        return entry.get("id")

    def _extract_date(self, entry: dict) -> datetime | None:
        """Extrai data de publicação."""
        date_str = (
            entry.get("published")
            or entry.get("pubDate")
            or entry.get("updated")
            or entry.get("dc:date")
        )

        if not date_str:
            return None

        try:
            if isinstance(date_str, datetime):
                return date_str

            # Tentar parser de data flexível
            return date_parser.parse(date_str)
        except Exception as e:
            log.debug(f"Erro ao parsear data '{date_str}': {e}")
            return None

    def _extract_authors(self, entry: dict) -> list[dict[str, str]]:
        """Extrai autores do artigo com papéis (author/editor)."""
        authors_list = []
        role = 'author'

        # Heurística para detectar se é um editorial
        title = self._extract_title(entry).lower()
        if 'editorial' in title:
            role = 'editor'

        # 1. Tentar authors (lista de dicts)
        if "authors" in entry and isinstance(entry["authors"], list):
            for author in entry["authors"]:
                if isinstance(author, dict) and "name" in author:
                    authors_list.append({'name': author["name"], 'role': role})
            if authors_list:
                return authors_list

        # 2. Tentar dc_creator (pode ser lista ou string)
        # Prioridade maior que 'author' simples, e comum em feeds acadêmicos
        dc_creator = entry.get("dc_creator") or entry.get("creator")
        if dc_creator:
            if isinstance(dc_creator, list):
                # Se for lista, processar cada um
                for creator in dc_creator:
                     authors_list.append({'name': str(creator), 'role': role})
                return authors_list
            elif isinstance(dc_creator, str):
                # Se for string, pode ser "A, B, C"
                names = self._split_authors(dc_creator)
                return [{'name': name, 'role': role} for name in names]

        # 3. Tentar author (string)
        author_str = entry.get("author", "")
        # Processar string única com spliter
        names = self._split_authors(author_str)
        return [{'name': name, 'role': role} for name in names]

    def parse_html_authors(self, html_content: str) -> list[dict[str, str]]:
        """Extrai autores de meta tags HTML (fallback para feeds incompletos)."""
        authors = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Tentar citation_author (Google Scholar / Highwire Press)
            meta_authors = soup.find_all("meta", {"name": "citation_author"})
            if not meta_authors:
                # Tentar dc.creator
                meta_authors = soup.find_all("meta", {"name": "dc.creator"})
            
            for tag in meta_authors:
                content = tag.get("content", "").strip()
                if content:
                    # Springer format: "Surname, Firstname" -> maintain as is or normalize?
                    # Our normalizer handles "Surname, Firstname".
                    authors.append({'name': content, 'role': 'author'}) 
                    
        except Exception as e:
            log.error(f"Erro ao parsear HTML para autores: {e}")
            
        return authors

    def _split_authors(self, author_str: str) -> list[str]:
        """Divide string de autores em lista usando regex robusto."""
        if not author_str:
            return []

        # Limpeza inicial
        # Remover "By " ou "Por " do início
        author_str = re.sub(r"^(By|Por|Autor:|Author:)\s+", "", author_str, flags=re.IGNORECASE)
        # Remover "et al."
        author_str = re.sub(r"\s+et\s+al\.?", "", author_str, flags=re.IGNORECASE)

        # 1. Tratar formato "email (Name)" ou "Name (email)" comum em Blogger/Atom
        # Ex: "noreply@blogger.com (Tameika Meadows" -> "Tameika Meadows"
        email_paren_match = re.search(r'[\w\.-]+@[\w\.-]+\s*\(([^)]+)\)', author_str)
        if email_paren_match:
            return [self._clean_author_name(email_paren_match.group(1))]
            
        name_paren_email_match = re.search(r'([^)]+)\s*\([\w\.-]+@[\w\.-]+\)', author_str)
        if name_paren_email_match:
            return [self._clean_author_name(name_paren_email_match.group(1))]

        # Regex para separar por vírgula, "e", "and", etc.
        # Mas CUIDADO com sufixos de titulação: "Name, PhD", "Name, BCBA"
        # Lista de sufixos para NÃO separar ou para remover
        credentials = r'\b(PhD|M\.?S\.?|B\.?C\.?B\.?A\.?(-D)?|M\.?A\.?|Dr\.?|R\.?B\.?T\.?|L\.?M\.?F\.?T\.?|L\.?C\.?S\.?W\.?)\b'
        
        # Primeiro, remover credenciais da string para evitar split incorreto nelas
        # Ex: "Tameika Meadows, BCBA" -> "Tameika Meadows"
        clean_str = re.sub(rf',\s*{credentials}', '', author_str, flags=re.IGNORECASE)
        clean_str = re.sub(rf'\s+{credentials}', '', clean_str, flags=re.IGNORECASE)

        names = re.split(r',\s*|\s+and\s+|\s+e\s+|\s+&\s+|\s*\|\s*', clean_str, flags=re.IGNORECASE)
        
        cleaned_names = []
        for name in names:
            clean = self._clean_author_name(name)
            if clean:
                cleaned_names.append(clean)
                
        return cleaned_names

    def _clean_author_name(self, name: str) -> str | None:
        """Limpa e valida um nome de autor."""
        name = name.strip()
        
        # Remover parenteses e emails residuais
        name = re.sub(r'\([^)]*\)', '', name).strip()
        name = re.sub(r'[\w\.-]+@[\w\.-]+', '', name).strip()
        name = re.sub(r'\)', '', name).strip()  # Remover parentes soltos
        
        if len(name) < 2:
            return None
            
        # Blacklist de termos genéricos
        blacklist = [
            "admin", "noreply", "editor", "author", "blog author", "contributor",
            "unknown", "anonymous", "staff", "team", "guest", "bhub"
        ]
        
        if name.lower() in blacklist:
            return None
            
        # Remover prefixos/sufixos comuns
        name = re.sub(r'^(Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.)\s+', '', name, flags=re.IGNORECASE)
        
        return name if len(name) > 1 else None

    def _extract_keywords(self, entry: dict) -> str | None:
        """Extrai keywords do artigo."""
        keywords = []

        # Campo tags
        tags = entry.get("tags", [])
        for tag in tags:
            if isinstance(tag, dict):
                term = tag.get("term", "")
                if term:
                    keywords.append(term)
            elif isinstance(tag, str):
                keywords.append(tag)

        # Campo category
        category = entry.get("category")
        if category:
            if isinstance(category, str):
                keywords.append(category)
            elif isinstance(category, list):
                keywords.extend(category)

        # dc:subject
        subject = entry.get("dc_subject") or entry.get("subject")
        if subject:
            if isinstance(subject, str):
                keywords.append(subject)
            elif isinstance(subject, list):
                keywords.extend(subject)

        if keywords:
            # Deduplificar e unir
            unique = list(dict.fromkeys(keywords))
            return ", ".join(unique[:20])  # Limitar a 20 keywords

        return None

    def _extract_doi(self, entry: dict) -> str | None:
        """Extrai DOI do artigo."""
        # Campo doi direto
        doi = entry.get("doi") or entry.get("prism_doi") or entry.get("dc_identifier")

        if doi:
            # Extrair apenas o DOI se for URL
            match = re.search(r"10\.\d{4,}/[^\s]+", doi)
            if match:
                return match.group(0)
            return doi

        # Procurar no link
        link = self._extract_url(entry)
        if link:
            match = re.search(r"10\.\d{4,}/[^\s]+", link)
            if match:
                return match.group(0)

        return None

    def _extract_journal(self, entry: dict) -> str | None:
        """Extrai nome do periódico."""
        return (
            entry.get("prism_publicationname")
            or entry.get("dc_source")
            or entry.get("source")
        )

    def _detect_language(self, entry: dict) -> str:
        """Detecta idioma do artigo."""
        # Campo language
        lang = entry.get("language") or entry.get("dc_language")
        if lang:
            return lang[:2].lower()

        # Heurística básica pelo título
        title = self._extract_title(entry)
        if title:
            # Verificar caracteres portugueses
            if any(c in title.lower() for c in ["ã", "õ", "ç", "á", "é", "í", "ó", "ú"]):
                return "pt"
            # Verificar caracteres espanhóis
            if "ñ" in title.lower():
                return "es"

        return "en"

    def _extract_image(self, entry: dict) -> str | None:
        """Extrai URL de imagem do artigo."""
        # Campo media:content
        media = entry.get("media_content", [])
        if media and isinstance(media, list):
            for m in media:
                if isinstance(m, dict) and "url" in m:
                    if m.get("medium") == "image" or "image" in m.get("type", ""):
                        return m["url"]

        # Campo media:thumbnail
        thumbnail = entry.get("media_thumbnail", [])
        if thumbnail and isinstance(thumbnail, list):
            for t in thumbnail:
                if isinstance(t, dict) and "url" in t:
                    return t["url"]

        # Procurar no content
        abstract = self._extract_abstract(entry)
        if abstract:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', abstract)
            if match:
                return match.group(1)

        # Campo enclosure
        enclosures = entry.get("enclosures", [])
        for enc in enclosures:
            if isinstance(enc, dict):
                if "image" in enc.get("type", ""):
                    return enc.get("url") or enc.get("href")

        return None
