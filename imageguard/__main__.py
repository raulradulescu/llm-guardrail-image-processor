"""Allow running as: python -m imageguard"""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
