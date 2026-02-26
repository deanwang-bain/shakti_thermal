"""CLI sanity tool for app data loading and checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from utils.data import load_data_catalog
from utils.sanity import run_startup_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Shakti app datasets and sanity checks")
    parser.add_argument("--root", type=str, default=".", help="Project root path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    catalog = load_data_catalog(str(root))
    checks = run_startup_checks(catalog)

    print("=== Dataset status ===")
    for key, status in catalog.statuses.items():
        print(f"{key:20s} loaded={status.loaded:<5} file={status.selected_file} warning={status.warning or '-'}")

    print("\n=== Sanity checks ===")
    for c in checks:
        print(f"[{c.status.upper():4s}] {c.name}: {c.message}")


if __name__ == "__main__":
    main()
