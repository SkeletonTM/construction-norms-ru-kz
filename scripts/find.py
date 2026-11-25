#!/usr/bin/env python3
"""Find catalog cards by number, title, scope or status."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def load():
    cards = []
    for path in sorted(CATALOG.glob("*/*.yaml")):
        card = yaml.safe_load(path.read_text(encoding="utf-8"))
        card["_path"] = str(path.relative_to(ROOT))
        cards.append(card)
    return cards


def matches(card, query, scope, status, jurisdiction, kind):
    if scope and scope not in (card.get("scope") or []):
        return False
    if status and card.get("status") != status:
        return False
    if jurisdiction and card.get("jurisdiction") != jurisdiction:
        return False
    if kind and card.get("kind") != kind:
        return False
    if not query:
        return True
    needle = query.lower()
    haystack = " ".join(
        str(card.get(field, "")) for field in ("id", "kind", "number", "title", "notes", "edition")
    ).lower()
    return needle in haystack or bool(re.search(re.escape(needle).replace(r"\ ", ""), haystack))


def main():
    parser = argparse.ArgumentParser(description="Поиск по каталогу нормативных документов")
    parser.add_argument("query", nargs="?", default="", help="номер, название или id")
    parser.add_argument("--scope", help="раздел: ov, vk, ss, pozh, obshchie (полный список в _schema.md)")
    parser.add_argument("--status", help="статус: действует, заменён, отменён, не_проверено")
    parser.add_argument("--jurisdiction", help="ru, kz или both")
    parser.add_argument("--kind", help="ГОСТ, СП, СН РК, СП РК, НТП РК")
    parser.add_argument("--all", action="store_true", help="включать заменённые документы")
    args = parser.parse_args()

    cards = load()
    hits = [
        c
        for c in cards
        if matches(c, args.query, args.scope, args.status, args.jurisdiction, args.kind)
    ]
    if not args.all and not args.status:
        hits = [c for c in hits if c.get("status") != "заменён"]

    if not hits:
        print("ничего не найдено")
        return 1

    for card in hits:
        print(f"{card['kind']} {card['number']} — {card['title']}")
        bits = [card["status"], card.get("jurisdiction", "")]
        if card.get("edition"):
            bits.append(card["edition"])
        if card.get("superseded_by"):
            bits.append(f"заменён на {card['superseded_by']}")
        print(f"    {'; '.join(b for b in bits if b)}")
        print(f"    {card['_path']}")
    print(f"\nнайдено: {len(hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
