"""
Serviço de processamento de PDFs.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF
import pdfplumber

from app.config import settings
from app.core.exceptions import DuplicateError, PDFProcessingError
from app.core.logging import log
from app.models import ProcessingStatus


class PDFService:
    """Serviço para processamento de arquivos PDF."""

    MAX_FILE_SIZE = settings.max_pdf_size_mb * 1024 * 1024  # MB para bytes
    ALLOWED_MIME_TYPES = ["application/pdf"]

    def __init__(self):
        self.upload_path = settings.pdf_upload_path

    async def process_pdf(
        self,
        file: BinaryIO,
        filename: str,
    ) -> dict:
        """
        Processa um arquivo PDF e extrai metadados.
        
        Args:
            file: Arquivo PDF em bytes
            filename: Nome original do arquivo
            
        Returns:
            dict com dados extraídos do PDF
        """
        log.info(f"Processando PDF: {filename}")

        # Ler conteúdo
        content = file.read()

        # Validar
        self._validate_pdf(content, filename)

        # Calcular hash
        file_hash = hashlib.sha256(content).hexdigest()

        # Extrair metadados
        metadata = self._extract_metadata(content)
        text = self._extract_text(content)

        # Extrair informações do texto
        extracted = self._extract_article_info(text, metadata)

        # Gerar caminho de salvamento
        save_path = self._generate_save_path(filename)

        # Salvar arquivo
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(content)

        log.info(f"PDF salvo em: {save_path}")

        return {
            "file_path": str(save_path),
            "file_size": len(content),
            "file_hash": file_hash,
            "original_filename": filename,
            "page_count": metadata.get("page_count"),
            "word_count": len(text.split()) if text else 0,
            "extracted_text": text[:50000] if text else None,  # Limitar texto
            "pdf_info": metadata,
            "title": extracted.get("title"),
            "abstract": extracted.get("abstract"),
            "authors": extracted.get("authors", []),
            "doi": extracted.get("doi"),
            "keywords": extracted.get("keywords"),
        }

    def _validate_pdf(self, content: bytes, filename: str):
        """Valida o arquivo PDF."""
        # Verificar tamanho
        if len(content) > self.MAX_FILE_SIZE:
            raise PDFProcessingError(
                f"Arquivo muito grande. Máximo: {settings.max_pdf_size_mb}MB"
            )

        # Verificar magic bytes do PDF
        if not content.startswith(b"%PDF"):
            raise PDFProcessingError("Arquivo não é um PDF válido")

        # Verificar extensão
        if not filename.lower().endswith(".pdf"):
            raise PDFProcessingError("Extensão do arquivo deve ser .pdf")

        # Tentar abrir para validar estrutura
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            if doc.page_count == 0:
                raise PDFProcessingError("PDF não contém páginas")
            doc.close()
        except fitz.FileDataError as e:
            raise PDFProcessingError(f"PDF corrompido ou inválido: {e}")

    def _extract_metadata(self, content: bytes) -> dict:
        """Extrai metadados do PDF usando PyMuPDF."""
        try:
            doc = fitz.open(stream=content, filetype="pdf")

            metadata = {
                "page_count": doc.page_count,
                "title": doc.metadata.get("title"),
                "author": doc.metadata.get("author"),
                "subject": doc.metadata.get("subject"),
                "keywords": doc.metadata.get("keywords"),
                "creator": doc.metadata.get("creator"),
                "producer": doc.metadata.get("producer"),
                "creation_date": doc.metadata.get("creationDate"),
                "mod_date": doc.metadata.get("modDate"),
            }

            doc.close()
            return metadata

        except Exception as e:
            log.error(f"Erro ao extrair metadados do PDF: {e}")
            return {"page_count": 0}

    def _extract_text(self, content: bytes) -> str:
        """Extrai texto do PDF."""
        text_parts = []

        # Tentar PyMuPDF primeiro (mais rápido)
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()

            text = "\n".join(text_parts)
            if text.strip():
                return text

        except Exception as e:
            log.warning(f"PyMuPDF falhou, tentando pdfplumber: {e}")

        # Fallback para pdfplumber (melhor para alguns PDFs)
        try:
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            return "\n".join(text_parts)

        except Exception as e:
            log.error(f"Erro ao extrair texto do PDF: {e}")
            return ""

    def _extract_article_info(self, text: str, metadata: dict) -> dict:
        """Extrai informações do artigo do texto."""
        info = {
            "title": None,
            "abstract": None,
            "authors": [],
            "doi": None,
            "keywords": None,
        }

        if not text:
            # Usar metadados do PDF
            info["title"] = metadata.get("title")
            info["authors"] = self._parse_authors_string(metadata.get("author", ""))
            info["keywords"] = metadata.get("keywords")
            return info

        # Extrair título (geralmente nas primeiras linhas)
        lines = text.split("\n")
        title_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                if not any(x in line.lower() for x in ["abstract", "resumo", "doi:", "http"]):
                    title_lines.append(line)
                    if len(" ".join(title_lines)) > 50:
                        break

        if title_lines:
            info["title"] = " ".join(title_lines)
        elif metadata.get("title"):
            info["title"] = metadata["title"]

        # Extrair abstract
        abstract_match = re.search(
            r"(?:abstract|resumo)[:\s]*(.{100,2000}?)(?=\n\n|introduction|introdução|keywords|palavras)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if abstract_match:
            info["abstract"] = abstract_match.group(1).strip()

        # Extrair DOI
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", text)
        if doi_match:
            info["doi"] = doi_match.group(0)

        # Extrair keywords
        keywords_match = re.search(
            r"(?:keywords|palavras[- ]?chave)[:\s]*(.{10,500}?)(?=\n\n|abstract|introduction)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if keywords_match:
            info["keywords"] = keywords_match.group(1).strip()
        elif metadata.get("keywords"):
            info["keywords"] = metadata["keywords"]

        # Extrair autores (mais complexo, usar metadados se disponível)
        if metadata.get("author"):
            info["authors"] = self._parse_authors_string(metadata["author"])

        return info

    def _parse_authors_string(self, authors_str: str) -> list[str]:
        """Parse string de autores em lista."""
        if not authors_str:
            return []

        # Separadores comuns
        separators = [";", " and ", " & ", ","]

        authors = [authors_str]
        for sep in separators:
            new_authors = []
            for a in authors:
                new_authors.extend(a.split(sep))
            authors = new_authors

        # Limpar e filtrar
        cleaned = []
        for a in authors:
            a = a.strip()
            if a and len(a) > 2:
                cleaned.append(a)

        return cleaned[:20]

    def _generate_save_path(self, filename: str) -> Path:
        """Gera caminho para salvar o PDF."""
        now = datetime.utcnow()
        year_month = now.strftime("%Y/%m")

        # Sanitizar nome do arquivo
        safe_name = re.sub(r"[^\w\-.]", "_", filename)

        # Adicionar timestamp para evitar conflitos
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        name_parts = safe_name.rsplit(".", 1)

        if len(name_parts) == 2:
            final_name = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
        else:
            final_name = f"{safe_name}_{timestamp}.pdf"

        return self.upload_path / year_month / final_name

    async def check_duplicate(self, file_hash: str, db) -> bool:
        """Verifica se PDF já existe pelo hash."""
        from sqlalchemy import select
        from app.models import PDFMetadata

        result = await db.execute(
            select(PDFMetadata).where(PDFMetadata.file_hash == file_hash)
        )
        return result.scalar_one_or_none() is not None

    def delete_pdf(self, file_path: str) -> bool:
        """Remove arquivo PDF do sistema."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                log.info(f"PDF removido: {file_path}")
                return True
            return False
        except Exception as e:
            log.error(f"Erro ao remover PDF: {e}")
            return False

    def get_pdf_info(self, file_path: str) -> dict | None:
        """Retorna informações de um PDF existente."""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            content = path.read_bytes()
            doc = fitz.open(stream=content, filetype="pdf")

            info = {
                "file_size": path.stat().st_size,
                "page_count": doc.page_count,
                "metadata": doc.metadata,
            }

            doc.close()
            return info

        except Exception as e:
            log.error(f"Erro ao obter info do PDF: {e}")
            return None
