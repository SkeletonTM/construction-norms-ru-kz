#!/usr/bin/env python3
"""Build catalog/README.md and catalog/index.json from YAML cards."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

JURISDICTION_TITLES = {
    "ru": "Россия",
    "kz": "Казахстан",
    "both": "Россия и Казахстан",
}
JURISDICTION_NOTE = {
    "ru": "Действуют только в РФ.",
    "kz": "Действуют только в РК.",
    "both": "Межгосударственные документы, применяемые в обеих странах.",
}
SCOPE_TITLES = {
    "ov": "ОВ",
    "vk": "ВК",
    "teplo": "Теплотехника",
    "pozh": "Пожарная безопасность",
    "ps": "ПС",
    "os": "ОС",
    "skud": "СКУД",
    "ss": "СС",
    "avtomatika": "Автоматизация",
    "elektro": "Электроснабжение",
    "ar": "АР",
    "obshchie": "Общие",
    "gaz": "Газоснабжение",
    "naruzh": "Наружные сети",
    "osnovaniya": "Основания и изыскания",
    "konstrukcii": "Конструкции",
    "inzashchita": "Инженерная защита",
    "organizaciya": "Организация строительства",
    "dostupnost": "Доступность",
    "grafo": "Градостроительство",
    "special": "Специальные здания",
}
STATUS_ORDER = ["действует", "частично_действует", "заменён", "отменён", "не_проверено"]
STATUS_MARK = {
    "действует": "действует",
    "частично_действует": "частично",
    "заменён": "заменён",
    "отменён": "отменён",
    "не_проверено": "не проверено",
}


def load():
    cards = []
    for path in sorted(CATALOG.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["_path"] = str(path.relative_to(ROOT))
        data["_rel"] = str(path.relative_to(CATALOG))
        data["_dir"] = path.parent.name
        cards.append(data)
    return cards


def sort_key(card):
    rank = STATUS_ORDER.index(card.get("status")) if card.get("status") in STATUS_ORDER else len(STATUS_ORDER)
    return (rank, card.get("title", ""))


def label(card):
    return f"{card['kind']} {card['number']}"


def main():
    cards = load()
    if not cards:
        print(f"каталог пуст: {CATALOG}", file=sys.stderr)
        return 1

    index = []
    for card in sorted(cards, key=lambda c: (c["jurisdiction"], sort_key(c))):
        index.append(
            {
                "id": card["id"],
                "kind": card["kind"],
                "number": card["number"],
                "title": card["title"],
                "jurisdiction": card["jurisdiction"],
                "status": card["status"],
                "scope": card.get("scope", []),
                "edition": card.get("edition"),
                "introduced": str(card["introduced"]) if card.get("introduced") else None,
                "superseded_by": card.get("superseded_by"),
                "path": card["_path"],
            }
        )

    (CATALOG / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Каталог нормативных документов",
        "",
        "Сгенерирован из YAML-карточек командой `python3 scripts/build_index.py`. "
        "Правьте карточки, а не этот файл.",
        "",
        f"Всего документов: **{len(cards)}** — "
        + ", ".join(
            f"{JURISDICTION_TITLES[j]}: {sum(1 for c in cards if c['jurisdiction'] == j)}"
            for j in ("ru", "kz", "both")
        ),
        "",
    ]

    for jur in ("ru", "kz", "both"):
        group = sorted([c for c in cards if c["jurisdiction"] == jur], key=sort_key)
        lines += [f"## {JURISDICTION_TITLES[jur]}", "", JURISDICTION_NOTE[jur], ""]
        if not group:
            lines += ["_Пока пусто._", ""]
            continue
        lines += ["| Документ | Название | Статус | Редакция | Разделы |", "| --- | --- | --- | --- | --- |"]
        for card in group:
            scopes = ", ".join(SCOPE_TITLES.get(s, s) for s in card.get("scope", []))
            edition = card.get("edition") or ""
            status = STATUS_MARK.get(card["status"], card["status"])
            if card.get("superseded_by"):
                status += f" → {card['superseded_by']}"
            lines.append(
                f"| [{label(card)}]({card['_rel']}) | {card['title']} | {status} | {edition} | {scopes} |"
            )
        lines.append("")

    lines += [
        "## Обозначения",
        "",
        "- **ОВ** — отопление, вентиляция, кондиционирование.",
        "- **ВК** — водоснабжение и канализация.",
        "- **Теплотехника** — тепловая защита, изоляция, тепловые сети.",
        "- **Пожарная безопасность** — эвакуация, огнестойкость, противопожарный водопровод.",
        "- **ПС** — пожарная сигнализация и автоматика пожаротушения.",
        "- **ОС** — охранная сигнализация, охранное телевидение, антитеррор.",
        "- **СКУД** — контроль и управление доступом.",
        "- **СС** — системы связи, электросвязь, оповещение.",
        "- **Автоматизация** — диспетчеризация инженерных систем.",
        "- **Электроснабжение** — электроустановки зданий.",
        "- **АР** — архитектура и состав проектной документации.",
        "- **Общие** — документы, нужные всем разделам.",
        "- **Газоснабжение** — газораспределение и газопотребление.",
        "- **Наружные сети** — наружные водопровод, канализация, площадки.",
        "- **Основания и изыскания** — изыскания, фундаменты, земляные работы.",
        "- **Конструкции** — металл, бетон, дерево, камень, кровля, полы.",
        "- **Инженерная защита** — защита территорий, обследование зданий.",
        "- **Организация строительства** — производство и приёмка работ.",
        "- **Доступность** — маломобильные группы населения.",
        "- **Градостроительство** — планировка и застройка.",
        "- **Специальные здания** — школы, спорт, паркинги, многофункциональные.",
        "",
        "Статус `заменён → id` означает, что документ отменён и заменён указанной карточкой.",
        "",
    ]

    (CATALOG / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"карточек: {len(cards)}; обновлены catalog/README.md и catalog/index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
