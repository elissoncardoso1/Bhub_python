"""
Serviço de processamento de PDFs.
"""

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

import fitz  # PyMuPDF
import pdfplumber
from sqlalchemy import select

from app.config import settings
from app.core.exceptions import PDFProcessingError
from app.core.logging import log
from app.models import Article, PDFMetadata, ProcessingStatus


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
        """
        Valida o arquivo PDF de forma robusta.
        Previne uploads maliciosos com JavaScript, objetos perigosos, etc.
        """
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

        # Validações de segurança: verificar conteúdo perigoso
        content_lower = content.lower()

        # Bloquear JavaScript embutido
        if b'/javascript' in content_lower or b'/js' in content_lower:
            raise PDFProcessingError("PDF contém JavaScript, não permitido por segurança")

        # Bloquear ações perigosas
        dangerous_actions = [b'/launch', b'/gotor', b'/uri', b'/submitform', b'/resetform']
        for action in dangerous_actions:
            if action in content_lower:
                raise PDFProcessingError(
                    f"PDF contém ações perigosas ({action.decode('utf-8', errors='ignore')}), não permitido"
                )

        # Limitar complexidade: contar objetos
        object_count = content.count(b'obj')
        if object_count > 10000:
            raise PDFProcessingError(
                f"PDF muito complexo ({object_count} objetos). Máximo permitido: 10000"
            )

        # Verificar se não é um zip bomb (PDFs podem conter streams comprimidos)
        # Limitar tamanho após descompressão estimada (PDFs geralmente comprimem 2-3x)
        estimated_decompressed = len(content) * 3
        if estimated_decompressed > self.MAX_FILE_SIZE * 10:
            raise PDFProcessingError("PDF pode ser um zip bomb (tamanho descomprimido estimado muito grande)")

        # Tentar abrir para validar estrutura
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            if doc.page_count == 0:
                raise PDFProcessingError("PDF não contém páginas")

            # Validar que não há páginas excessivas (possível DoS)
            if doc.page_count > 1000:
                raise PDFProcessingError(
                    f"PDF contém muitas páginas ({doc.page_count}). Máximo permitido: 1000"
                )

            doc.close()
        except fitz.FileDataError as e:
            raise PDFProcessingError(f"PDF corrompido ou inválido: {e}")
        except Exception as e:
            # Capturar outros erros de processamento
            log.warning(f"Erro ao validar PDF: {e}")
            raise PDFProcessingError(f"Erro ao processar PDF: {e}")

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
            if (
                line
                and 10 < len(line) < 200
                and not any(x in line.lower() for x in ["abstract", "resumo", "doi:", "http"])
            ):
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

        # Sanitizar extensão e gerar nome seguro via UUID
        safe_ext = re.sub(r"[^a-z0-9.]", "", Path(filename).suffix.lower()) or ".pdf"
        final_name = f"{uuid.uuid4().hex}{safe_ext}"

        target_path = (self.upload_path / year_month / final_name).resolve()
        base_path = self.upload_path.resolve()
        if not str(target_path).startswith(str(base_path)):
            raise PDFProcessingError("Caminho inválido para salvar PDF")

        return target_path

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

    async def process_article_pdf(
        self,
        article_id: int,
        pdf_url: str | None = None,
        db: Any | None = None,
    ) -> dict[str, Any] | None:
        """Operação transacional explícita: baixa e persiste o PDF de um artigo.

        Concentra obtenção do artigo, resolução da URL, download, validação,
        extração de metadados, persistência e commit/rollback controlado
        (T1.3 do plano BHub v1.1 — desacopla jobs de background_tasks).

        Args:
            article_id: ID do artigo alvo.
            pdf_url: URL explícita do PDF. Quando ausente, usa ``article.pdf_url``
                ou URLs derivadas de ``article.original_url``.
            db: Sessão existente (ex.: job ARQ). Quando ausente, cria a própria
                sessão via ``get_session_context``.

        Returns:
            dict com ``article_id``/``file_path``/``file_hash`` em caso de
            sucesso; ``None`` quando não há trabalho a fazer (artigo ausente,
            já possui PDF, não é open access, sem URL, download falhou ou
            duplicata).

        Raises:
            Exception: erros inesperados propagam após rollback — jobs ARQ
            usam o retry do worker.
        """
        if db is not None:
            return await self._process_article_pdf(article_id, pdf_url, db)

        from app.database import get_session_context

        async with get_session_context() as session:
            return await self._process_article_pdf(article_id, pdf_url, session)

    async def _process_article_pdf(
        self,
        article_id: int,
        pdf_url: str | None,
        db: Any,
    ) -> dict[str, Any] | None:
        downloaded_file_path: str | None = None
        try:
            result = await db.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()

            if not article:
                log.warning(f"Artigo {article_id} não encontrado para download de PDF")
                return None

            if article.pdf_file_path:
                log.info(f"Artigo {article_id} já possui PDF: {article.pdf_file_path}")
                return None

            if not article.is_open_access:
                log.debug(f"Artigo {article_id} não é open access, pulando download")
                return None

            pdf_data = await self._download_article_pdf(article, pdf_url, db)
            if not pdf_data:
                log.warning(f"Não foi possível baixar PDF para artigo {article_id}")
                return None

            # T1.4 (idempotência): caminho do arquivo baixado — se a
            # persistência falhar ou for duplicata, o arquivo é removido
            # para não deixar órfãos (a reexecução baixaria de novo).
            downloaded_file_path = pdf_data["file_path"]

            # Verificar duplicata novamente (pode ter sido adicionada por outra task)
            if await self.check_duplicate(pdf_data["file_hash"], db):
                log.info(
                    f"PDF duplicado detectado para artigo {article_id}, removendo arquivo"
                )
                Path(pdf_data["file_path"]).unlink(missing_ok=True)
                return None

            article.pdf_file_path = pdf_data["file_path"]
            article.pdf_file_size = pdf_data["file_size"]

            pdf_meta_result = await db.execute(
                select(PDFMetadata).where(PDFMetadata.article_id == article_id)
            )
            pdf_metadata = pdf_meta_result.scalar_one_or_none()

            if pdf_metadata:
                pdf_metadata.file_hash = pdf_data["file_hash"]
                pdf_metadata.original_filename = pdf_data["original_filename"]
                pdf_metadata.page_count = pdf_data.get("page_count")
                pdf_metadata.word_count = pdf_data.get("word_count")
                pdf_metadata.extracted_text = pdf_data.get("extracted_text")
                pdf_metadata.pdf_info = str(pdf_data.get("pdf_info", {}))
                pdf_metadata.processing_status = ProcessingStatus.COMPLETED
                pdf_metadata.processing_error = None
            else:
                pdf_metadata = PDFMetadata(
                    article_id=article_id,
                    file_hash=pdf_data["file_hash"],
                    original_filename=pdf_data["original_filename"],
                    page_count=pdf_data.get("page_count"),
                    word_count=pdf_data.get("word_count"),
                    extracted_text=pdf_data.get("extracted_text"),
                    pdf_info=str(pdf_data.get("pdf_info", {})),
                    processing_status=ProcessingStatus.COMPLETED,
                )
                db.add(pdf_metadata)

            await db.commit()
            log.info(
                f"PDF baixado e associado ao artigo {article_id}: {pdf_data['file_path']}"
            )
            return {
                "article_id": article_id,
                "file_path": pdf_data["file_path"],
                "file_hash": pdf_data["file_hash"],
            }
        except Exception:
            await db.rollback()
            # T1.4 (idempotência): rollback sem arquivo órfão — senão a
            # reexecução do job baixaria um segundo arquivo e duplicaria
            # em disco o que não foi persistido.
            if downloaded_file_path:
                Path(downloaded_file_path).unlink(missing_ok=True)
                log.warning(
                    f"Arquivo não persistido removido após rollback: {downloaded_file_path}"
                )
            raise

    async def _download_article_pdf(
        self,
        article: Any,
        pdf_url: str | None,
        db: Any,
    ) -> dict | None:
        """Resolve a URL (explícita, campo do artigo ou derivadas) e baixa o PDF."""
        if pdf_url:
            return await self.download_pdf_from_url(pdf_url, article.title, db)

        article_pdf_url = article.pdf_url
        if article_pdf_url:
            return await self.download_pdf_from_url(article_pdf_url, article.title, db)

        if article.original_url:
            potential_urls = [
                article.original_url.replace("/article/", "/pdf/"),
                article.original_url.replace("/article/", "/download/"),
                article.original_url + ".pdf",
                article.original_url + "/pdf",
            ]
            for url in potential_urls:
                log.info(f"Tentando baixar PDF de: {url}")
                pdf_data = await self.download_pdf_from_url(url, article.title, db)
                if pdf_data:
                    return pdf_data
            return None

        log.warning(f"Artigo {article.id} não tem URL do artigo nem PDF URL")
        return None

    async def download_pdf_from_url(
        self,
        pdf_url: str,
        article_title: str,
        db,
    ) -> dict | None:
        """
        Baixa um PDF de uma URL e processa.

        Args:
            pdf_url: URL do PDF para baixar
            article_title: Título do artigo (para nome do arquivo)
            db: Sessão do banco de dados

        Returns:
            dict com dados do PDF processado ou None se falhar
        """
        from urllib.parse import urlparse

        import httpx

        log.info(f"Baixando PDF de: {pdf_url}")

        # Validar URL (prevenir SSRF)
        parsed = urlparse(pdf_url)
        if parsed.scheme not in ['http', 'https']:
            log.error(f"URL inválida: {pdf_url}")
            return None

        # Validar que é realmente um PDF
        if not (pdf_url.lower().endswith('.pdf') or 'pdf' in pdf_url.lower()):
            log.warning(f"URL não parece ser um PDF: {pdf_url}")
            # Mas vamos tentar mesmo assim, pode ser um redirect

        try:
            # Fazer download com timeout
            async with httpx.AsyncClient(
                timeout=60.0,  # Timeout maior para PDFs
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/pdf, */*",
                },
            ) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()

                # Verificar content-type
                content_type = response.headers.get("content-type", "").lower()
                if "pdf" not in content_type and not pdf_url.lower().endswith('.pdf'):
                    log.warning(f"Content-Type não é PDF: {content_type}")
                    # Mas vamos processar mesmo assim

                # Ler conteúdo
                content = response.content

                # Validar tamanho
                if len(content) > self.MAX_FILE_SIZE:
                    log.error(f"PDF muito grande: {len(content)} bytes (máximo: {self.MAX_FILE_SIZE})")
                    return None

                # Validar que é um PDF válido
                if not content.startswith(b"%PDF"):
                    log.error("Arquivo baixado não é um PDF válido")
                    return None

                # Gerar nome de arquivo seguro
                safe_title = re.sub(r"[^\w\-.]", "_", article_title[:100])
                filename = f"{safe_title}.pdf"

                # Processar PDF usando o método existente
                import io
                file_obj = io.BytesIO(content)
                pdf_data = await self.process_pdf(file_obj, filename)

                # Verificar duplicata
                if await self.check_duplicate(pdf_data["file_hash"], db):
                    log.info(f"PDF já existe no sistema (hash: {pdf_data['file_hash'][:8]}...)")
                    # T1.4 (idempotência): hash já persistido em outro artigo —
                    # o arquivo recém-salvo é órfão e deve ser removido para
                    # que a reexecução do job não acumule duplicatas em disco.
                    Path(pdf_data["file_path"]).unlink(missing_ok=True)
                    return None

                log.info(f"PDF baixado e processado com sucesso: {pdf_data['file_path']}")
                return pdf_data

        except httpx.TimeoutException:
            log.error(f"Timeout ao baixar PDF: {pdf_url}")
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Erro HTTP ao baixar PDF: {e.response.status_code} - {pdf_url}")
            return None
        except Exception as e:
            log.error(f"Erro ao baixar PDF de {pdf_url}: {e}")
            return None
