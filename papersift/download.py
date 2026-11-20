"""Download PDFs and write the metadata JSON next to them."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from papersift.models import Paper
from papersift.utils import sanitize_filename

USER_AGENT = "papersift (https://github.com/RAHAMNIabdelkaderseifelislem/papersift)"


class DownloadError(Exception):
    """A PDF could not be downloaded."""


def safe_id(arxiv_id: str) -> str:
    """Old-style arXiv ids contain a slash (hep-th/9901001); make them file-safe."""
    return arxiv_id.replace("/", "_")


def pdf_filename(paper: Paper, score: int) -> str:
    return f"{score}-{paper.year}-{sanitize_filename(paper.title)}.pdf"


def download_pdf(paper: Paper, dest: Path, session=None, timeout: float = 60.0) -> Path:
    """Download ``paper``'s PDF to ``dest`` (written atomically)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        response = session.get(
            paper.pdf_url, timeout=timeout, headers={"User-Agent": USER_AGENT}, stream=True
        )
        if response.status_code != 200:
            raise DownloadError(f"HTTP {response.status_code} for {paper.pdf_url}")
        with open(tmp, "wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                handle.write(chunk)
        os.replace(tmp, dest)
    except requests.RequestException as exc:
        raise DownloadError(f"Could not download {paper.pdf_url}: {exc}") from exc
    finally:
        if tmp.exists():
            tmp.unlink()
    return dest


def write_metadata(paper: Paper, assessments: dict, pdf_path: Path | None, metadata_dir: Path, score: int) -> Path:
    """Write ``<score>-<year>-<title>_metadata.json`` and return its path."""
    metadata_dir = Path(metadata_dir)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    data = {
        **paper.to_dict(),
        "final_score": score,
        "local_pdf_path": str(pdf_path) if pdf_path else None,
        "assessments": assessments,
    }
    path = metadata_dir / f"{score}-{paper.year}-{sanitize_filename(paper.title)}_metadata.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
