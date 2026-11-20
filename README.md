# PaperSift

**An Open-Source AI Research Assistant for Academic Paper Discovery and Evaluation.**

PaperSift is an LLM-powered research assistant that helps researchers
discover, evaluate, rank, and organize academic papers based on their
research interests.

It combines academic search, structured relevance assessment,
multi-provider LLM integration, and automated paper retrieval
into a unified workflow.

> **Project status:** Pre-release / alpha.
>
> The core CLI, multi-provider support, two-stage ranking, and caching
> are implemented. The graphical interface is being integrated.
> The first public PyPI release is planned for version 0.1.0.

## Why

Starting a literature review means reading hundreds of abstracts to find the few papers worth your time. `papersift` was first built at the start of a PhD to do that triage automatically, and it was used to select the papers behind a published systematic survey (see [Citation](#citation)).

## Features

- **Project-aware relevance scoring.** You describe your research project once; every paper is scored against it.
- **Two-stage ranking.** Every result is triaged from its abstract; with `--fulltext`, the best ones are then read in full (introduction, method and conclusion) for a more reliable score.
- **Rubric-based scores.** The model only fills a small rubric (topic match, method match, novelty); the 0-100 score is computed in code, so it is reproducible and comparable across models.
- **Many LLM providers.** Local Ollama, Gemini, and any OpenAI-compatible API (Groq, OpenRouter, Together, Cerebras, Mistral, OpenAI, or your own `--base-url`), with automatic retry on rate limits and optional fallback to a backup provider.
- **Explainable results.** Each saved paper comes with its scores, strengths, limitations and reasoning.
- **Local cache.** Papers already scored are not scored again, so re-running is cheap.
- **Optional GUI** *(in development)*.

## Installation

PaperSift is preparing for its first PyPI release.

### Install from source

```bash
git clone https://github.com/RAHAMNIabdelkaderseifelislem/papersift.git
cd papersift

python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[fulltext]"
```

With full-text ranking:

```bash
pip install "papersift[fulltext]"
```

For development:

```bash
git clone https://github.com/RAHAMNIabdelkaderseifelislem/papersift.git
cd papersift
python -m venv venv
source venv/bin/activate        # Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -e ".[dev,fulltext]"
pytest
```

Requires Python 3.10 or newer.

## Quick start

### Command line

With a local model (no API key):

```bash
papersift run "Generative AI methods for autonomous agents" --provider ollama --model <model-name>
```

With a free online provider:

```bash
export GROQ_API_KEY=...        # Windows PowerShell: $env:GROQ_API_KEY="..."
papersift run "Generative AI methods for autonomous agents" \
  --provider groq --model <model-name> \
  --threshold 80 --since-days 365 --fulltext -v
```

With a backup provider if the first one fails or hits its rate limit:

```bash
papersift run "my project" --provider groq --model <model-a> --fallback gemini=<model-b>
```

List the available providers with `papersift providers`, and all options with `papersift run --help`.

### Python

```python
from papersift import Scout
from papersift.providers import create_provider

provider = create_provider("groq", "<model-name>")
scout = Scout(
    "Generative AI methods for autonomous agents",
    provider,
    relevance_threshold=80,
    fulltext=True,
)
for result in scout.run():
    print(result.score, result.paper.title, result.pdf_path)
```

Model names change often, so look up the current free models on your provider's website.

## Configuration

API keys are read from environment variables, never from code or command-line arguments. Copy `.env.example` to `.env` and fill in only the providers you use; `papersift` loads `.env` automatically.

| Provider | Variable |
|---|---|
| `gemini` | `GEMINI_API_KEY` |
| `groq` | `GROQ_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `together` | `TOGETHER_API_KEY` |
| `cerebras` | `CEREBRAS_API_KEY` |
| `mistral` | `MISTRAL_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `openai_compat` (with `--base-url`) | `OPENAI_COMPAT_API_KEY` |
| `ollama` | none (the Ollama server must be running) |

> Never commit your `.env` file. It is already listed in `.gitignore`.

## Output

Results are saved in the folder you choose (default `papersift_output/`):

```
papersift_output/
  pdfs/        # downloaded PDFs, named <score>-<year>-<title>.pdf
  metadata/    # one JSON file per paper: authors, abstract, arXiv id,
               # scores and the reasoning behind them
  .cache/      # SQLite cache and temporary downloads
```

## How it works

1. An LLM turns your project description into precise academic search keywords.
2. The arXiv API returns candidate papers from the date window you set.
3. **Stage 1:** each abstract is scored against your project with a rubric.
4. **Stage 2** (`--fulltext`): the best papers are downloaded and scored again from their full text; both scores are blended (the full text counts more).
5. Papers above your threshold are saved with their metadata and explanations.

## Roadmap

### Core
- [x] arXiv paper discovery
- [x] Multi-provider LLM integration
- [x] Retry and provider fallback
- [x] Rubric-based relevance scoring
- [x] SQLite caching and deduplication
- [x] Command-line interface
- [x] Optional full-text ranking

### Application
- [ ] Graphical user interface integration
- [ ] Unified CLI and GUI configuration
- [ ] End-to-end application testing

### Distribution
- [ ] First PyPI release (0.1.0)
- [ ] Installation and packaging verification
- [ ] Public documentation

### Future
- [ ] Additional academic sources (Semantic Scholar, OpenAlex)
- [ ] Extended export formats
- [ ] Improved research project management

## Contributing

Contributions are welcome, from first-time contributors too.

1. Open an issue to discuss what you want to work on, or pick one labeled `good first issue`.
2. Create a branch from `main` (`git checkout -b feature/short-description`).
3. Make your change and add or update tests (`pytest`).
4. Open a pull request describing what you changed and why.

Please keep pull requests small and focused so they are easy to review.

## Citation

PaperSift was developed to support academic literature discovery
and research paper selection.

If you use PaperSift in your research, please cite the software
using the citation information provided in `CITATION.cff`.

### Associated research publication

The development of PaperSift supported the literature discovery
and paper selection process for the following publication:

Rahmani, Abedelkader Seif El Islem, Yahiaoui, Yasser & Bouziane,
Abdelghani.

"Architectural Patterns for Self-Improving Intelligent Agents:
A Systematic Survey of Generative and Cognitive Approaches."

SN Computer Science, 7, 746 (2026).

https://doi.org/10.1007/s42979-026-05333-6


## Software Authors

- Abedelkader Seif El Islem Rahmani
- Mohammed Bennour

## License

Released under the MIT License. See `LICENSE` for details.
