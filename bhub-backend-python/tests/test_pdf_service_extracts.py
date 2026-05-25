
from app.services.pdf_service import PDFService


def test_extract_metadata_from_fitz(monkeypatch):
    service = PDFService()

    class FakeDoc:
        page_count = 2
        metadata = {
            "title": "T",
            "author": "A",
            "subject": "S",
            "keywords": "K",
            "creator": "C",
            "producer": "P",
            "creationDate": "D1",
            "modDate": "D2",
        }

        def close(self):
            pass

    monkeypatch.setattr("app.services.pdf_service.fitz.open", lambda *args, **kwargs: FakeDoc())
    meta = service._extract_metadata(b"%PDF-1.4\n")
    assert meta["page_count"] == 2
    assert meta["title"] == "T"


def test_extract_text_uses_fitz(monkeypatch):
    service = PDFService()

    class FakePage:
        def __init__(self, text):
            self._text = text

        def get_text(self):
            return self._text

    class FakeDoc(list):
        def __init__(self):
            super().__init__([FakePage("a"), FakePage("b")])

        def close(self):
            pass

    monkeypatch.setattr("app.services.pdf_service.fitz.open", lambda *args, **kwargs: FakeDoc())
    text = service._extract_text(b"%PDF-1.4\n")
    assert text == "a\nb"


def test_extract_text_fallback_pdfplumber(monkeypatch):
    service = PDFService()

    def fail_open(*_args, **_kwargs):
        raise Exception("fail")

    class FakePDF:
        pages = [type("P", (), {"extract_text": lambda self: "x"})()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.services.pdf_service.fitz.open", fail_open)
    monkeypatch.setattr("app.services.pdf_service.pdfplumber.open", lambda *_args, **_kwargs: FakePDF())
    text = service._extract_text(b"%PDF-1.4\n")
    assert text == "x"
