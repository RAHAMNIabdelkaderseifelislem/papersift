# papersift

**Find the papers that matter to your research, automatically.**

`papersift` is an LLM-powered agent that searches arXiv for papers related to your research project, scores how relevant each one is, and downloads the best ones together with structured metadata. It works with local models and with most free online LLM API providers.

> **Status:** alpha (0.1.0). The command-line tool, multi-provider support, two-stage ranking and caching work. The optional GUI is still in development. See the [Roadmap](#roadmap).

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

```bash
pip install papersift
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

- [x] Prototype: arXiv search, abstract scoring with a local model, PDF and metadata download
- [x] Common provider interface (Ollama, OpenAI-compatible, Gemini)
- [x] Retry with backoff and provider fallback
- [x] Fixed arXiv query building and date-window parameter
- [x] Rubric-based scoring with robust JSON parsing
- [x] SQLite cache and deduplication
- [x] Command-line interface
- [x] Full-text ranking stage
- [ ] Optional GUI
- [ ] First PyPI release
- [ ] More paper sources (for example Semantic Scholar, OpenAlex)

## Contributing

Contributions are welcome, from first-time contributors too.

1. Open an issue to discuss what you want to work on, or pick one labeled `good first issue`.
2. Create a branch from `main` (`git checkout -b feature/short-description`).
3. Make your change and add or update tests (`pytest`).
4. Open a pull request describing what you changed and why.

Please keep pull requests small and focused so they are easy to review.

## Citation

If `papersift` helps your research, please cite the survey whose paper selection it supported:

> *Architectural Patterns for Self-Improving Intelligent Agents: A Systematic Survey of Generative and Cognitive Approaches.* SN Computer Science. https://doi.org/10.1007/s42979-026-05333-6

A `CITATION.cff` file describes how to cite the software itself.

## Contributors

- **Seif El Islem** (lead developer)
- Contributors are listed here as they join.

## License

Released under the MIT License. See `LICENSE` for details.
