# papersift

**Find the papers that matter to your research, automatically.**

`papersift` is an LLM-powered agent that searches arXiv for papers related to your research project, scores how relevant each one is, and downloads the best ones together with structured metadata. It works with local models and with most free online LLM API providers.

> **Status:** early development (pre-release). The original prototype works with a local Ollama model and scores papers from their abstracts. The multi-provider support, full-text ranking and GUI described below are being built now. See the [Roadmap](#roadmap).

## Why

Starting a literature review means reading hundreds of abstracts to find the few papers worth your time. `papersift` was first built at the start of a PhD to do that triage automatically, and it was used to select the papers behind a published systematic survey (see [Citation](#citation)).

## Features

- **Project-aware relevance scoring.** You describe your research project once; every paper is scored against it.
- **Two-stage ranking** *(in progress)*:
  1. cheap triage of every result from its abstract;
  2. deeper scoring of only the top papers from their full text.
- **Many LLM providers** *(in progress)*: local Ollama, Gemini, and any OpenAI-compatible API (for example Groq, OpenRouter, Together, Cerebras, Mistral) through one common interface, with retry on rate limits and optional fallback between providers.
- **Explainable results.** Each paper gets a score, key strengths, limitations and a recommendation, saved next to the PDF.
- **Local cache** *(in progress)*: papers already processed are skipped on later runs.
- **Optional GUI** *(in progress)*: a simple web interface for people who prefer not to use the command line.

## Installation

Once published on PyPI:

```bash
pip install papersift
```

With the optional extras:

```bash
pip install "papersift[gui]"       # web interface
pip install "papersift[fulltext]"  # full-text ranking (PDF text extraction)
```

For development:

```bash
git clone https://github.com/RAHAMNIabdelkaderseifelislem/papersift.git
cd papersift
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

Requires Python 3.10 or newer.

## Quick start

The interface below is the target design and may change before the first release.

### Command line

```bash
papersift run "Generative AI methods for autonomous agents" \
  --provider groq \
  --model <model-name> \
  --threshold 80 \
  --since-days 365
```

### Python

```python
from papersift import Scout

scout = Scout(
    project_title="Generative AI methods for autonomous agents",
    provider="groq",
    model="<model-name>",
    relevance_threshold=80,
)
results = scout.run(max_results=100)
```

### GUI

```bash
papersift gui
```

## Configuration

API keys are read from environment variables, never from code. Copy `.env.example` to `.env` and fill in only the providers you use:

```bash
OPENAI_COMPAT_API_KEY=...
GEMINI_API_KEY=...
```

Local Ollama needs no key; just make sure the Ollama server is running and the model is pulled.

> Never commit your `.env` file. It is already listed in `.gitignore`.

## Output

Downloaded papers and their metadata are saved in a folder you choose (default `papersift_output/`):

```
papersift_output/
  pdfs/        # downloaded PDFs, named by score, year and title
  metadata/    # one JSON file per paper: authors, abstract, arXiv id,
               # scores and the reasoning behind them
```

## How it works

1. An LLM turns your project description into precise academic search keywords.
2. The arXiv API returns candidate papers from the date window you set.
3. **Stage 1:** each abstract is scored against your project with a rubric.
4. **Stage 2:** the top papers are downloaded and scored again from their full text.
5. Papers above your threshold are saved with their metadata and explanations.

## Roadmap

- [x] Prototype: arXiv search, abstract scoring with a local model, PDF and metadata download
- [ ] Common provider interface (Ollama, OpenAI-compatible, Gemini)
- [ ] Retry with backoff and provider fallback
- [ ] Fixed arXiv query building and date-window parameter
- [ ] Rubric-based scoring with robust JSON parsing
- [ ] SQLite cache and deduplication
- [ ] Command-line interface
- [ ] Full-text ranking stage
- [ ] Optional GUI
- [ ] Tests, documentation and first PyPI release
- [ ] More paper sources (for example Semantic Scholar, OpenAlex)

## Contributing

Contributions are welcome, from first-time contributors too.

1. Open an issue to discuss what you want to work on, or pick one labeled `good first issue`.
2. Create a branch from `main` (`git checkout -b feature/short-description`).
3. Make your change and add or update tests.
4. Open a pull request describing what you changed and why.

Please keep pull requests small and focused so they are easy to review.

## Citation

If `papersift` helps your research, please cite the survey whose paper selection it supported:

> *Architectural Patterns for Self-Improving Intelligent Agents: A Systematic Survey of Generative and Cognitive Approaches.* SN Computer Science. https://doi.org/10.1007/s42979-026-05333-6

A `CITATION.cff` file will be added to the repository for the software itself.

## Contributors

- **Seif El Islem** (lead developer)
- Contributors are listed here as they join.

## License

Released under the MIT License. See `LICENSE` for details.
