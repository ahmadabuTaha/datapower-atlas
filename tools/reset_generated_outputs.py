#!/usr/bin/env python3

from pathlib import Path
import shutil
import argparse


KEEP_FILES = {
    ".gitkeep",
}


def clean_directory(path: Path):
    if not path.exists():
        return

    for item in path.iterdir():
        if item.name in KEEP_FILES:
            continue

        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--domain",
        help="Clean only one domain, e.g. STG or STG_REPLICA",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean all generated index/report outputs",
    )

    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]

    index_root = root / "index"
    reports_root = root / "reports"
    unified_root = root / "unified"

    if args.domain:
        domain = args.domain.upper().replace(" ", "_")

        targets = [
            index_root / domain,
            reports_root / domain,
        ]

        for target in targets:
            print(f"Cleaning: {target}")
            clean_directory(target)
            target.mkdir(parents=True, exist_ok=True)

        print(f"\nDomain reset complete: {domain}")
        return

    if args.all:
        print(f"Cleaning all generated index data: {index_root}")
        clean_directory(index_root)

        print(f"Cleaning all reports: {reports_root}")
        clean_directory(reports_root)

        print(f"Cleaning unified outputs: {unified_root}")
        clean_directory(unified_root)

        for domain in ["STG", "STG_REPLICA"]:
            (index_root / domain).mkdir(parents=True, exist_ok=True)
            (reports_root / domain).mkdir(parents=True, exist_ok=True)

        unified_root.mkdir(parents=True, exist_ok=True)

        print("\nFull generated-output reset complete.")
        return

    parser.error("Use either --domain DOMAIN or --all")


if __name__ == "__main__":
    main()