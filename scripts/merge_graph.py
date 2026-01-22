#!/usr/bin/env python3
"""
Trigger KG duplicate merging via the Endstate API.

Usage:
  python scripts/merge_graph.py
  python scripts/merge_graph.py --labels Skill,Concept,Topic
  python scripts/merge_graph.py --match-property name
  python scripts/merge_graph.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request


def _call_merge(base_url: str, label: str, match_property: str) -> dict:
    query = urllib.parse.urlencode({
        "label": label,
        "match_property": match_property,
    })
    url = f"{base_url.rstrip('/')}/api/merge?{query}"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger KG duplicate merging via the API.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--labels", default="Skill,Concept,Topic")
    parser.add_argument("--match-property", default="name")
    args = parser.parse_args()

    labels = [label.strip() for label in args.labels.split(",") if label.strip()]
    if not labels:
        raise SystemExit("Provide at least one label.")
    if args.match_property not in {"name", "id"}:
        raise SystemExit("match-property must be 'name' or 'id'.")

    for label in labels:
        result = _call_merge(args.base_url, label, args.match_property)
        merged = result.get("merged_count", 0)
        message = result.get("message", "")
        print(f"{label}: merged {merged} duplicates. {message}".strip())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
