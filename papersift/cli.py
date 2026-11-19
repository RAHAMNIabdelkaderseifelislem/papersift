"""Command-line interface (to be built)."""

from papersift import __version__


def main() -> None:
    print(f"papersift {__version__}")


if __name__ == "__main__":
    main()