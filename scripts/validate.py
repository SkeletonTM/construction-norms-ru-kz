#!/usr/bin/env python3
"""Validate catalog YAML cards against _schema.md."""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

KINDS = {"ГОСТ", "ГОСТ Р", "СНиП", "СНиП РК", "СП", "СН РК", "СП РК", "НТП РК", "СТ РК", "СТО НОСТРОЙ", "Приказ"}
STATUSES = {"действует", "частично_действует", "заменён", "отменён", "не_проверено"}
SCOPES = {
    "ov", "vk", "teplo", "pozh", "ps", "os", "skud",
    "ss", "avtomatika", "elektro", "ar", "obshchie",
    "gaz", "naruzh", "osnovaniya", "konstrukcii", "inzashchita",
    "organizaciya", "dostupnost", "grafo", "special",
}
SOURCE_KINDS = {"текст", "статус", "магазин", "приказ"}
JURISDICTIONS = {"ru", "kz", "both"}
SOFT_LINK_HOSTS = {"docs.cntd.ru"}


def soft_host(url):
    """Return the lowercase hostname, or None if the URL is malformed."""
    if not isinstance(url, str):
        return None
    try:
        host = urllib.parse.urlparse(url).hostname
    except ValueError:
        return None
    return host.lower().rstrip(".") if host else None


def link_verdict(url, code):
    """Classify a link result: hard error, warning, or ok."""
    host = soft_host(url)
    if host is None or host in SOFT_LINK_HOSTS:
        return "warning"
    if code in (404, 410):
        return "error"
    if code is None or code >= 400:
        return "warning"
    return "ok"


def pluralize(n, one, few, many):
    """Pick the Russian noun form for n."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


REQUIRED = ["id", "kind", "number", "title", "jurisdiction", "status", "scope", "sources", "updated"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*$")


def load_cards():
    cards = {}
    errors = []
    for path in sorted(CATALOG.glob("*/*.yaml")):
        rel = path.relative_to(ROOT)
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: не читается как YAML: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: ожидался объект, получено {type(data).__name__}")
            continue
        data["_path"] = rel
        data["_dir"] = path.parent.name
        cid = data.get("id")
        if cid in cards:
            errors.append(f"{rel}: id '{cid}' уже занят файлом {cards[cid]['_path']}")
            continue
        cards[cid] = data
    return cards, errors


def check_card(card, cards):
    errs, warns = [], []
    rel, cdir = card["_path"], card["_dir"]

    for field in REQUIRED:
        if field not in card or card[field] in ("", None, []):
            errs.append(f"{rel}: нет обязательного поля '{field}'")

    if card.get("id") and card["_path"].stem != card["id"]:
        errs.append(f"{rel}: id '{card['id']}' не совпадает с именем файла")

    if card.get("id") and not ID_RE.match(card["id"]):
        errs.append(f"{rel}: id '{card['id']}' не по шаблону {ID_RE.pattern}")

    if card.get("kind") and card["kind"] not in KINDS:
        errs.append(f"{rel}: вид '{card['kind']}' не из {sorted(KINDS)}")

    status = card.get("status")
    if status and status not in STATUSES:
        errs.append(f"{rel}: статус '{status}' не из {sorted(STATUSES)}")

    jur = card.get("jurisdiction")
    if jur:
        if jur not in JURISDICTIONS:
            errs.append(f"{rel}: юрисдикция '{jur}' не из {sorted(JURISDICTIONS)}")
        elif jur != cdir:
            errs.append(f"{rel}: jurisdiction '{jur}' не совпадает с каталогом '{cdir}'")

    for scope in card.get("scope") or []:
        if scope not in SCOPES:
            errs.append(f"{rel}: раздел '{scope}' не из {sorted(SCOPES)}")

    if not card.get("scope"):
        warns.append(f"{rel}: пустой список разделов")
    elif len(set(card["scope"])) != len(card["scope"]):
        errs.append(f"{rel}: дубликаты в scope")

    sources = card.get("sources")
    if sources is not None:
        if not isinstance(sources, list) or not sources:
            errs.append(f"{rel}: sources должен быть непустым списком")
        else:
            for i, src in enumerate(sources):
                if not isinstance(src, dict):
                    errs.append(f"{rel}: sources[{i}] не объект")
                    continue
                if not src.get("url"):
                    errs.append(f"{rel}: sources[{i}] без url")
                elif not str(src["url"]).startswith(("http://", "https://")):
                    errs.append(f"{rel}: sources[{i}] url не http(s)")
                if src.get("kind") not in SOURCE_KINDS:
                    errs.append(f"{rel}: sources[{i}] kind '{src.get('kind')}' не из {sorted(SOURCE_KINDS)}")

    for field in ("updated", "introduced", "source_checked"):
        value = card.get(field)
        if value is None:
            continue
        if not DATE_RE.match(str(value)):
            errs.append(f"{rel}: '{field}' не в формате YYYY-MM-DD: {value}")
            continue
        try:
            dt.date.fromisoformat(str(value))
        except ValueError:
            errs.append(f"{rel}: '{field}' не существует: {value}")

    if status == "заменён" and not card.get("superseded_by"):
        errs.append(f"{rel}: статус 'заменён' требует 'superseded_by'")
    if card.get("superseded_by") and status != "заменён":
        errs.append(f"{rel}: есть 'superseded_by', но статус '{status}'")

    if status == "не_проверено" and card.get("todo") is not True:
        errs.append(f"{rel}: статус 'не_проверено' требует 'todo: true'")
    if card.get("todo") is True and status != "не_проверено":
        warns.append(f"{rel}: todo: true, но статус '{status}'")

    target = card.get("superseded_by")
    if target:
        other = cards.get(target)
        if other is None:
            errs.append(f"{rel}: superseded_by '{target}' — такой карточки нет")
        elif card.get("id") not in (other.get("supersedes") or []):
            errs.append(f"{rel}: superseded_by '{target}', но у '{target}' нет ссылки на '{card.get('id')}' в 'supersedes'")

    for prev in card.get("supersedes") or []:
        other = cards.get(prev)
        if other is None:
            errs.append(f"{rel}: supersedes '{prev}' — такой карточки нет")
        elif other.get("superseded_by") != card["id"]:
            errs.append(f"{rel}: supersedes '{prev}', но у '{prev}' нет 'superseded_by: {card['id']}'")

    if status == "действует" and card.get("superseded_by"):
        errs.append(f"{rel}: действующий документ не может быть заменён")

    return errs, warns


def check_links(cards, timeout=20):
    """Return (hard_errors, skipped_count, probed_count).

    docs.cntd.ru blocks automated requests, so its links are reported as
    skipped instead of failing CI. Dead links on other hosts stay hard errors.
    """
    errs = []
    seen = set()
    skipped = set()
    probed = 0
    for card in cards.values():
        for src in card.get("sources") or []:
            url = src.get("url")
            if url is None or url == "":
                continue
            if not isinstance(url, str):
                errs.append(f"{card['_path']}: ссылка не строка: {url!r}")
                continue
            if url in seen:
                continue
            seen.add(url)
            host = soft_host(url)
            if host is None:
                errs.append(f"{card['_path']}: некорректная ссылка {url!r}")
                continue
            if host in SOFT_LINK_HOSTS:
                skipped.add(url)
                continue
            code = probe(url, timeout)
            probed += 1
            if link_verdict(url, code) == "error":
                errs.append(f"{card['_path']}: ссылка {url} отвечает {code}")
    return errs, len(skipped), probed


def probe(url, timeout):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; norm-catalog-check/1.0)",
            "Accept-Language": "ru",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Проверка карточек каталога нормативных документов")
    parser.add_argument("--links", action="store_true", help="дополнительно проверить доступность ссылок")
    parser.add_argument("--strict", action="store_true", help="предупреждения считать ошибками")
    args = parser.parse_args()

    cards, errors = load_cards()
    if not cards and not errors:
        errors.append(f"каталог пуст: {CATALOG}")

    warnings = []
    for card in cards.values():
        errs, warns = check_card(card, cards)
        errors.extend(errs)
        warnings.extend(warns)

    checked = 0
    if args.links:
        link_errs, skipped, checked = check_links(cards)
        errors.extend(link_errs)
        if skipped:
            hosts = ", ".join(sorted(SOFT_LINK_HOSTS))
            verb = pluralize(skipped, "пропущена", "пропущено", "пропущено")
            noun = pluralize(skipped, "ссылка", "ссылки", "ссылок")
            host_noun = pluralize(len(SOFT_LINK_HOSTS), "сайт", "сайта", "сайтов")
            warnings.append(
                f"{verb} {skipped} {noun} на {hosts}: {host_noun} блокирует автоматические запросы"
            )

    for msg in warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {msg}")
    for msg in errors:
        print(f"ОШИБКА: {msg}")

    by_status = {}
    for card in cards.values():
        by_status[card.get("status", "?")] = by_status.get(card.get("status", "?"), 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items()))

    print(f"\nкарточек: {len(cards)} ({summary})")
    if args.links:
        print(f"проверено ссылок: {checked}")
    print(f"предупреждений: {len(warnings)}, ошибок: {len(errors)}")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
