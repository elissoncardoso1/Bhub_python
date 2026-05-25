from app.services.opengraph_service import OpenGraphService


def test_opengraph_wrap_and_truncate():
    service = OpenGraphService()
    font = service._load_font(12)
    long_text = "um texto muito longo para quebrar em linhas"

    lines = service._wrap_text(long_text, max_width=50, font=font, max_lines=2)
    assert len(lines) <= 2

    truncated = service._truncate_text(long_text, max_width=30, font=font)
    assert truncated.endswith("...") or truncated == long_text
