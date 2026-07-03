import pytest
from django.core.exceptions import ValidationError

from apps.library.upload_policy import validate_paper_import
from apps.repositories.upload_policy import validate_code_import


def test_paper_import_size_and_format_policy():
    validate_paper_import(filename="paper.pdf", content_type="application/pdf", size_bytes=100)
    validate_paper_import(filename="refs.bib", content_type="text/plain", size_bytes=100)

    with pytest.raises(ValidationError):
        validate_paper_import(filename="paper.pdf", size_bytes=51 * 1024 * 1024)

    with pytest.raises(ValidationError):
        validate_paper_import(filename="paper.docx", size_bytes=100)


def test_code_import_size_and_format_policy():
    validate_code_import(filename="source.zip", content_type="application/zip", size_bytes=100)
    validate_code_import(filename="source.tar.gz", content_type="application/gzip", size_bytes=100)

    with pytest.raises(ValidationError):
        validate_code_import(filename="source.zip", size_bytes=201 * 1024 * 1024)

    with pytest.raises(ValidationError):
        validate_code_import(filename="source.py", size_bytes=100)
