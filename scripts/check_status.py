#!/usr/bin/env python3
"""Check document statuses against registries and secondary reference sites.

РФ: files.stroyinf.ru (реестр) + docs.cntd.ru (вторичная карточка документа).
РК: prg.kz (Параграф, карточка «Информация о документе»).

Скрипт только сообщает расхождения. Статусы в карточках он не меняет:
решение о правке остаётся за человеком.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

STATUS_WORDS = {
    "действует": "действует",
    "введен впервые": "действует",
    "взамен": "действует",
    # «принят» описывает принятие МГС, а не действующий статус: в STATUS_WORDS
    # его нет намеренно, чтобы сверка не выдавала ложное совпадение.
    "не подлежит применению": "заменён",
    "заменен": "заменён",
    "заменён": "заменён",
    "утратил силу": "отменён",
    "не действует": "отменён",
    "отменен в рф": "отменён",
    "отменен": "отменён",
    "отменён": "отменён",
}
# Реестр отвечает и статусом, и видом введения. Отменённый документ может быть
# и «заменён», и «отменён» — для сверки это одна группа.
REPEALED = {"заменён", "отменён"}
# Строки реестра о приказах, письмах и изменениях описывают не сам документ.
ADMIN_PREFIXES = ("приказ", "письмо", "распоряжение", "изменение", "поправка",
                  "информационное письмо", "рекомендации", "постановление")


_OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)


def fetch(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "ru"})
    with _OPENER.open(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def text_of(page):
    page = re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.S)
    return html.unescape(" ".join(re.sub(r"<[^>]+>", " ", page).split()))


def stroyinf_rows(query):
    body = urllib.parse.urlencode(
        {"f1": query, "b": "2", "c1": "0", "c2": "3", "c3": "", "f3": "0"}
    ).encode()
    page = fetch("https://files.stroyinf.ru/cgi-bin/ecat/ecat.fcgi", body)
    rows = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        parts = html.unescape(" ".join(re.sub(r"<[^>]+>", "|", row).split()))
        parts = [p.strip() for p in re.sub(r"\|{2,}", "|", parts).split("|") if p.strip()]
        for i, part in enumerate(parts):
            if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", part) and i + 1 < len(parts):
                rows.append(
                    {"doc": " ".join(parts[:i]), "date": part, "status": parts[i + 1]}
                )
                break
    unique = {tuple(sorted(r.items())): r for r in rows}
    return list(unique.values())


MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def prg_status(doc_id):
    page = fetch(f"https://prg.kz/document/?doc_id={doc_id}")
    body = text_of(page)
    idx = body.find("Информация о документе")
    if idx < 0:
        return None
    window = body[idx : idx + 600]
    status = re.search(
        r"Статус:\s*(.+?)(?=\s+(?:Дата последнего изменения|Дата документа|введен|введено)\b|$)",
        window,
    )
    since = re.search(r"введен[а]? в действие с (\d{1,2}) (\w+) (\d{4})", window)
    iso = None
    if since and since.group(2) in MONTHS:
        iso = f"{since.group(3)}-{MONTHS[since.group(2)]:02d}-{int(since.group(1)):02d}"
    return {"status": status.group(1) if status else None, "since": iso}


def cntd_info(url):
    body = text_of(fetch(url))
    intro = re.search(r"Дата введения (\d{4}-\d{2}-\d{2})", body)
    return {"introduced": intro.group(1) if intro else None}


def card_number(card):
    return f"{card['kind']} {card['number']}"


def normalize(value):
    # Пробелы и тире сохраняются как разделители: по ним проверяются границы
    # обозначения перед названием документа.
    return re.sub(r"[\s\-–—]+", " ", value or "").strip()


def search_query(card):
    number = card["number"]
    if card["kind"] in ("СП", "СН", "СНиП") or re.match(r"^\d+\.\d+", number):
        return number.rsplit(".", 1)[0]
    return number


def row_matches(card, row):
    # Вид и номер должны совпадать целиком: ГОСТ != ГОСТ Р, 2405-88 != 2405-880.
    # Название после обозначения допускается, но приклеивать его к номеру нельзя.
    separator = r"[\s\-–—]*"
    parts = normalize(card["kind"]).split() + normalize(card["number"]).split()
    pattern = r"(?<!\w)" + separator.join(re.escape(p) for p in parts) + r"(?!\w)"
    return re.search(pattern, normalize(row["doc"])) is not None


def main():
    parser = argparse.ArgumentParser(description="Сверка статусов карточек с реестрами и справочниками")
    parser.add_argument("--jurisdiction", choices=["ru", "kz", "both"], help="ограничить юрисдикцию")
    parser.add_argument("--id", help="проверить одну карточку по id")
    parser.add_argument("--delay", type=float, default=1.5, help="пауза между запросами, сек")
    args = parser.parse_args()

    cards = []
    all_cards = {}
    for path in sorted(CATALOG.glob("*/*.yaml")):
        card = yaml.safe_load(path.read_text(encoding="utf-8"))
        card["_path"] = path.relative_to(ROOT).as_posix()
        all_cards[card["id"]] = card
        if args.id and card["id"] != args.id:
            continue
        if args.jurisdiction and card["jurisdiction"] != args.jurisdiction:
            continue
        cards.append(card)

    problems = 0
    for card in cards:
        print(f"\n{card_number(card)}  [{card['jurisdiction']}]  карточка: {card['status']}")
        prg_ids = [
            int(m.group(1))
            for src in card.get("sources") or []
            for m in [re.search(r"prg\.kz/document/\?doc_id=(\d+)", src.get("url", ""))]
            if m
        ]
        try:
            if prg_ids:
                info = prg_status(prg_ids[0])
                if info and info["status"]:
                    print(f"    prg.kz: {info['status']} (с {info['since']})")
                    if info["since"] and card.get("introduced") and info["since"] != str(card["introduced"]):
                        print(f"    РАСХОЖДЕНИЕ: реестр ввёл с {info['since']}, в карточке {card['introduced']}")
                        problems += 1
                    if info["status"].lower().startswith("действ") and card["status"] != "действует":
                        print("    РАСХОЖДЕНИЕ: реестр считает документ действующим")
                        problems += 1
                    if info["status"].lower().startswith(("утрат", "отмен", "не действ")) and card["status"] == "действует":
                        print("    РАСХОЖДЕНИЕ: реестр считает документ недействующим")
                        problems += 1
                else:
                    print("    prg.kz: статус не найден на странице")
            elif card["jurisdiction"] in ("ru", "both"):
                rows = stroyinf_rows(search_query(card))
                exact = [r for r in rows if row_matches(card, r)]
                if not exact:
                    seen = sorted(
                        {
                            m.group(0)
                            for r in rows
                            for m in [re.search(r"\d+\.\d{5}\s*\.\s*\d{4}", r["doc"])]
                            if m
                        }
                    )
                    print("    stroyinf: этой редакции нет в реестре")
                    if seen:
                        print(f"    stroyinf: в реестре есть {', '.join(seen)}")
                    cntd = next(
                        (s["url"] for s in card.get("sources") or [] if "docs.cntd.ru/document/" in s.get("url", "")),
                        None,
                    )
                    if cntd:
                        info = cntd_info(cntd)
                        if info["introduced"] and card.get("introduced"):
                            same = info["introduced"] == str(card["introduced"])
                            print(f"    docs.cntd.ru: дата введения {info['introduced']}"
                                  f"{' — совпадает' if same else ' — РАСХОЖДЕНИЕ'}")
                            if not same:
                                print(f"    РАСХОЖДЕНИЕ: в карточке {card['introduced']}")
                                problems += 1
                        elif info["introduced"]:
                            print(f"    docs.cntd.ru: дата введения {info['introduced']}, в карточке не указана")
                        else:
                            print("    docs.cntd.ru: дата введения не найдена")
                    else:
                        print("    статус не сверен — нет карточки docs.cntd.ru")
                order = next(
                    (s["url"] for s in card.get("sources") or [] if s.get("kind") == "приказ"), None
                )
                # Приказ о введении заменяющего документа тоже подтверждает отмену:
                # в тексте новой редакции стоит «ВВЕДЕН ВЗАМЕН».
                if not order:
                    successor = all_cards.get(card.get("superseded_by") or "")
                    if successor:
                        order = successor.get("enacted_by") or next(
                            (s["url"] for s in successor.get("sources") or []
                             if s.get("kind") == "приказ"), None
                        )
                marks = []
                for row in exact[:3]:
                    print(f"    stroyinf: {row['date']} — {row['status']}")
                    if row["status"] == "информационный документ":
                        continue
                    if row["doc"].strip().lower().startswith(ADMIN_PREFIXES):
                        continue
                    marks.append(STATUS_WORDS.get(row["status"].lower(), row["status"]))
                # Реестр может отдавать несколько записей об одном документе.
                # Совпала хотя бы одна — расхождения нет.
                if marks and card["status"] not in marks:
                    if card["status"] in REPEALED and REPEALED & set(marks):
                        continue
                    if card["status"] == "частично_действует" and "действует" in marks:
                        continue
                    successor = all_cards.get(card.get("superseded_by") or "")
                    if successor and successor.get("status") == "действует" and not order:
                        order = successor["id"]
                    if order and card["status"] == "заменён":
                        print(f"    реестр отстаёт: замена подтверждена документом-заменой ({order})")
                        continue
                    print(f"    РАСХОЖДЕНИЕ: реестр '{', '.join(sorted(set(marks)))}', карточка '{card['status']}'")
                    problems += 1
        except Exception as exc:
            print(f"    ошибка запроса: {exc}")
        time.sleep(args.delay)

    print(f"\nпроверено карточек: {len(cards)}, расхождений: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
