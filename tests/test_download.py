import json
from datetime import datetime, timezone

import pytest
import requests

from papersift.download import DownloadError, download_pdf, pdf_filename, safe_id, write_metadata
from papersift.models import Paper
from tests.conftest import FakeSession

PAPER = Paper("hep-th/9901001", "Héllo: A Title!", "abs", ["A"], datetime(2026, 2, 3, tzinfo=timezone.utc), "u", "http://x/p.pdf")


class StreamResponse:
    def __init__(self, status_code=200, chunks=(b"%PDF-", b"data")):
        self.status_code, self._chunks = status_code, chunks

    def iter_content(self, chunk_size):
        yield from self._chunks


def test_filenames():
    assert pdf_filename(PAPER, 91) == "91-2026-hello_a_title.pdf"
    assert safe_id("hep-th/9901001") == "hep-th_9901001"


def test_download_writes_file_atomically(tmp_path):
    dest = tmp_path / "pdfs" / "a.pdf"
    download_pdf(PAPER, dest, session=FakeSession([StreamResponse()]))
    assert dest.read_bytes() == b"%PDF-data"
    assert not list(tmp_path.rglob("*.part"))


def test_download_http_error(tmp_path):
    with pytest.raises(DownloadError, match="404"):
        download_pdf(PAPER, tmp_path / "a.pdf", session=FakeSession([StreamResponse(404)]))


def test_download_network_error_leaves_no_partial_file(tmp_path):
    with pytest.raises(DownloadError):
        download_pdf(PAPER, tmp_path / "a.pdf", session=FakeSession([requests.ConnectionError("x")]))
    assert not list(tmp_path.rglob("*.part")) and not (tmp_path / "a.pdf").exists()


def test_write_metadata(tmp_path):
    path = write_metadata(PAPER, {"abstract": {"score": 70}}, tmp_path / "a.pdf", tmp_path / "meta", 77)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "77-2026-hello_a_title_metadata.json"
    assert data["final_score"] == 77 and data["assessments"]["abstract"]["score"] == 70
    assert data["arxiv_id"] == "hep-th/9901001"
