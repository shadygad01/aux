"""Compatibility entrypoint for the monorepo CLI application."""

from apps.decision_cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
