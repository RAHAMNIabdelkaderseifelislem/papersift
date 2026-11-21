# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-21

### Added
- Common `LLMProvider` interface with Ollama, Gemini and OpenAI-compatible providers
  (Groq, OpenRouter, Together, Cerebras, Mistral, OpenAI), retry with backoff on rate limits,
  and an ordered fallback chain.
- arXiv source with exact-phrase keyword queries and a date window.
- Stage 1 abstract triage with rubric scoring (the 0-100 score is computed in code),
  tolerant JSON parsing and one automatic retry.
- Stage 2 full-text scoring of the top papers (optional `fulltext` extra, uses PyMuPDF).
- SQLite cache so papers already scored are not scored again.
- `papersift` command-line interface (`run`, `providers`).
- Continuous integration on Python 3.10 to 3.13.

### Changed
- Rewrote the original single-file prototype as a package (kept in `legacy/search.py`).
- Minimum Python version is now 3.10.
