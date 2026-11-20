"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys

from papersift import __version__
from papersift.core import Scout
from papersift.providers import (
    FallbackProvider,
    LLMProvider,
    ProviderError,
    available_providers,
    create_provider,
)
from papersift.sources import SourceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papersift", description="Find, rank and download research papers with an LLM."
    )
    parser.add_argument("--version", action="version", version=f"papersift {__version__}")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="search arXiv and download the most relevant papers")
    run.add_argument("project_title", help="short description of your research project")
    run.add_argument("--provider", default="ollama", help="LLM provider (see 'papersift providers')")
    run.add_argument("--model", required=True, help="model name for the provider")
    run.add_argument("--base-url", help="custom API base URL (required for openai_compat)")
    run.add_argument(
        "--fallback",
        action="append",
        default=[],
        metavar="PROVIDER=MODEL",
        help="backup provider used if the main one fails (repeatable)",
    )
    run.add_argument("--threshold", type=int, default=80, help="minimum score (0-100) to keep a paper")
    run.add_argument("--since-days", type=int, default=365, help="only papers from the last N days")
    run.add_argument("--max-results", type=int, default=100, help="maximum arXiv results to consider")
    run.add_argument("--keywords", type=int, default=6, help="number of search keywords to generate")
    run.add_argument("--output", default="papersift_output", help="output folder")
    run.add_argument("--no-cache", action="store_true", help="ignore previously saved scores")
    run.add_argument("-v", "--verbose", action="store_true", help="show detailed progress")

    sub.add_parser("providers", help="list the available LLM providers")
    return parser


def build_provider(args: argparse.Namespace) -> LLMProvider:
    main = create_provider(args.provider, args.model, base_url=args.base_url)
    if not args.fallback:
        return main
    chain = [main]
    for spec in args.fallback:
        name, sep, model = spec.partition("=")
        if not sep or not model:
            raise ProviderError(f"Invalid --fallback '{spec}'. Use PROVIDER=MODEL, e.g. gemini=gemini-2.0-flash")
        chain.append(create_provider(name, model))
    return FallbackProvider(chain)


def _run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s"
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
    )
    results = scout.run()
    if not results:
        print(f"No paper reached the threshold of {args.threshold}. Try lowering --threshold.")
        return 0
    print(f"\n{len(results)} relevant paper(s) saved in {args.output}/\n")
    for result in results:
        print(f"  {result.score:>3}  {result.paper.year}  {result.paper.title}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover - python-dotenv is a hard dependency
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "providers":
        print("\n".join(available_providers()))
        return 0
    if args.command == "run":
        try:
            return _run(args)
        except (ProviderError, SourceError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted. Scores already computed are cached.", file=sys.stderr)
            return 130
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
