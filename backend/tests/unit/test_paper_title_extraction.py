from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter

from apps.library.import_services import PaperImportError, extract_title_from_pdf_upload
from apps.library.models import PaperTitleExtractionResult


def _pdf_with_metadata(title: str) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title})
    writer.write(output)
    return output.getvalue()


def _pdf_with_first_page_text(text: str) -> bytes:
    content = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_at = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n".encode()
    )
    return output.getvalue()


def _upload(content: bytes, name: str = "paper.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_embedded_metadata_title_is_preferred_over_first_page_text():
    result = extract_title_from_pdf_upload(_upload(_pdf_with_metadata("Embedded Paper Title")))

    assert result.title == "Embedded Paper Title"
    assert result.source == PaperTitleExtractionResult.SourceAttempted.EMBEDDED_METADATA
    assert result.confidence == PaperTitleExtractionResult.Confidence.HIGH


def test_first_page_text_is_used_when_embedded_metadata_is_missing():
    result = extract_title_from_pdf_upload(
        _upload(_pdf_with_first_page_text("Visible Paper Title"))
    )

    assert result.title == "Visible Paper Title"
    assert result.source == PaperTitleExtractionResult.SourceAttempted.FIRST_PAGE_VISIBLE_TEXT
    assert result.confidence == PaperTitleExtractionResult.Confidence.MEDIUM


def test_missing_reliable_title_is_rejected():
    with pytest.raises(PaperImportError) as exc_info:
        extract_title_from_pdf_upload(_upload(_pdf_with_metadata("")))

    assert exc_info.value.reason == "missing_reliable_title"


def test_malformed_pdf_fails_title_extraction():
    with pytest.raises(PaperImportError) as exc_info:
        extract_title_from_pdf_upload(_upload(b"%PDF-1.4\nnot actually a pdf"))

    assert exc_info.value.reason == "unreadable_pdf"
