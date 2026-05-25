import pytest

from app.core.exceptions import PDFProcessingError
from app.services.pdf_service import PDFService


def test_pdf_validate_rejects_non_pdf():
    service = PDFService()
    with pytest.raises(PDFProcessingError):
        service._validate_pdf(b"NOTPDF", "file.pdf")


def test_pdf_validate_rejects_extension():
    service = PDFService()
    with pytest.raises(PDFProcessingError):
        service._validate_pdf(b"%PDF-1.4\n", "file.txt")


def test_pdf_validate_rejects_js():
    service = PDFService()
    with pytest.raises(PDFProcessingError):
        service._validate_pdf(b"%PDF-1.4\n/JavaScript", "file.pdf")


def test_pdf_validate_rejects_dangerous_action():
    service = PDFService()
    with pytest.raises(PDFProcessingError):
        service._validate_pdf(b"%PDF-1.4\n/Launch", "file.pdf")


def test_pdf_validate_ok(monkeypatch):
    service = PDFService()

    class FakeDoc:
        page_count = 1

        def close(self):
            pass

    monkeypatch.setattr("app.services.pdf_service.fitz.open", lambda *args, **kwargs: FakeDoc())
    service._validate_pdf(b"%PDF-1.4\n1 0 obj\n", "file.pdf")
