#!/usr/bin/env python3
"""
Remove legacy file-based project summaries.
"""
from pathlib import Path


def main() -> int:
    cache_dir = Path.home() / ".endstate" / "summaries"
    if not cache_dir.exists():
        print("No legacy summaries directory found.")
        return 0

    deleted = 0
    for path in cache_dir.glob("*.json"):
        try:
            path.unlink()
            deleted += 1
        except Exception as exc:
            print(f"Failed to delete {path}: {exc}")

    if deleted == 0:
        print("No legacy summary files removed.")
        return 0

    print(f"Deleted {deleted} legacy summary file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
