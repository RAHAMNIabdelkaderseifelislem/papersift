
"""Command-line interface for PaperSift."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path

from papersift import __version__
from papersift.core import Scout
from papersift.ranking.fulltext import FulltextError
from papersift.providers import (
    FallbackProvider,
    LLMProvider,
    ProviderError,
    available_providers,
    create_provider,
)
from papersift.sources import SourceError


def build_parser() -> argparse.ArgumentParser:
    formatter = argparse.ArgumentDefaultsHelpFormatter

    parser = argparse.ArgumentParser(
        prog="papersift",
        description=(
            "PaperSift - an LLM-powered research assistant for "
            "discovering, evaluating, ranking, and organizing academic papers."
        ),
        formatter_class=formatter,
        epilog=(
            "Examples:\n"
            "  papersift providers\n"
            '  papersift run "Autonomous AI agents" --model llama3\n'
            '  papersift run "LLM memory mechanisms" --provider gemini '
            '--model gemini-2.0-flash\n'
            "  papersift gui\n\n"
            "For command-specific options, use: papersift COMMAND --help"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"papersift {__version__}",
    )

    sub = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="COMMAND",
    )

    # --------------------------------------------------
    # Run command
    # --------------------------------------------------
    run = sub.add_parser(
        "run",
        help="search arXiv and rank relevant research papers",
        description=(
            "Search arXiv using keywords generated from your research "
            "project, evaluate paper relevance with an LLM, and save "
            "the results."
        ),
        formatter_class=formatter,
    )

    run.add_argument(
        "project_title",
        metavar="PROJECT_TITLE",
        help="short description of your research project",
    )

    run.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider to use (see 'papersift providers')",
    )

    run.add_argument(
        "--model",
        required=True,
        metavar="MODEL",
        help="model name for the selected provider",
    )

    run.add_argument(
        "--base-url",
        metavar="URL",
        help="custom API base URL (required for openai_compat)",
    )

    run.add_argument(
        "--fallback",
        action="append",
        default=[],
        metavar="PROVIDER=MODEL",
        help=(
            "backup provider if the primary provider fails; "
            "can be specified multiple times"
        ),
    )

    run.add_argument(
        "--threshold",
        type=int,
        default=80,
        metavar="SCORE",
        help="minimum relevance score (0-100) to keep a paper",
    )

    run.add_argument(
        "--since-days",
        type=int,
        default=365,
        metavar="DAYS",
        help="only consider papers published within the last N days",
    )

    run.add_argument(
        "--max-results",
        type=int,
        default=100,
        metavar="N",
        help="maximum number of arXiv results to consider",
    )

    run.add_argument(
        "--keywords",
        type=int,
        default=6,
        metavar="N",
        help="number of search keywords to generate",
    )

    run.add_argument(
        "--output",
        default="papersift_output",
        metavar="DIR",
        help="directory where research results will be saved",
    )

    run.add_argument(
        "--fulltext",
        action="store_true",
        help="also evaluate the full text of selected papers",
    )

    run.add_argument(
        "--triage-threshold",
        type=int,
        default=60,
        metavar="SCORE",
        help="minimum abstract score required for full-text evaluation",
    )

    run.add_argument(
        "--top-k",
        type=int,
        default=10,
        metavar="N",
        help="number of papers to evaluate using their full text",
    )

    run.add_argument(
        "--fulltext-weight",
        type=float,
        default=0.6,
        metavar="WEIGHT",
        help="weight assigned to the full-text score (0-1)",
    )

    run.add_argument(
        "--no-cache",
        action="store_true",
        help="ignore previously cached paper scores",
    )

    run.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="display detailed execution progress",
    )

    # --------------------------------------------------
    # Providers command
    # --------------------------------------------------
    sub.add_parser(
        "providers",
        help="list available LLM providers",
        description="Display all LLM providers supported by PaperSift.",
        formatter_class=formatter,
    )

    # --------------------------------------------------
    # GUI command
    # --------------------------------------------------
    sub.add_parser(
        "gui",
        help="launch the graphical user interface",
        description=(
            "Launch the PaperSift graphical interface using Streamlit. "
            "Requires the optional GUI dependencies."
        ),
        formatter_class=formatter,
    )

    return parser


def build_provider(args: argparse.Namespace) -> LLMProvider:
    main = create_provider(
        args.provider,
        args.model,
        base_url=args.base_url,
    )

    if not args.fallback:
        return main

    chain = [main]

    for spec in args.fallback:
        name, sep, model = spec.partition("=")

        if not sep or not name or not model:
            raise ProviderError(
                f"Invalid --fallback '{spec}'. "
                "Use PROVIDER=MODEL, e.g. gemini=gemini-2.0-flash"
            )

        chain.append(create_provider(name, model))

    return FallbackProvider(chain)


def _run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    provider = build_provider(args)

    scout = Scout(
        args.project_title,
        provider,
        relevance_threshold=args.threshold,
        since_days=args.since_days,
        max_results=args.max_results,
        n_keywords=args.keywords,
        output_dir=args.output,
        use_cache=not args.no_cache,
        fulltext=args.fulltext,
        triage_threshold=args.triage_threshold,
        top_k_fulltext=args.top_k,
        fulltext_weight=args.fulltext_weight,
    )

    results = scout.run()

    if not results:
        print(
            f"No paper reached the threshold of {args.threshold}. "
            "Try lowering --threshold."
        )
        return 0

    print(f"\n{len(results)} relevant paper(s) saved in {args.output}/\n")

    for result in results:
        print(
            f"  {result.score:>3}  "
            f"{result.paper.year}  "
            f"{result.paper.title}"
        )

    return 0


def _launch_gui() -> int:
    """Launch the Streamlit GUI."""

    if importlib.util.find_spec("streamlit") is None:
        print(
            "Error: Streamlit is not installed.\n"
            'Install the GUI dependencies with: pip install "papersift[gui]"',
            file=sys.stderr,
        )
        return 1

    app_path = Path(__file__).resolve().parent / "gui" / "app.py"

    if not app_path.is_file():
        print(
            f"Error: PaperSift GUI application was not found: {app_path}",
            file=sys.stderr,
        )
        return 1

    print("Launching PaperSift GUI...")

    try:
        return subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
            ]
        )
    except OSError as exc:
        print(f"Error launching GUI: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "providers":
        print("\n".join(available_providers()))
        return 0

    if args.command == "gui":
        return _launch_gui()

    if args.command == "run":
        try:
            return _run(args)
        except (
            ProviderError,
            SourceError,
            FulltextError,
            ValueError,
        ) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print(
                "\nInterrupted. Scores already computed are cached.",
                file=sys.stderr,
            )
            return 130

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
