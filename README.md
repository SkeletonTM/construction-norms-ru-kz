# Каталог нормативных документов для проектирования инженерных систем зданий

Справочник по действующим нормам России и Казахстана: ГОСТ, ГОСТ Р, СП, СНиП, СНиП РК, СН РК, СП РК, НТП РК, СТ РК. Один документ - одна YAML-карточка со статусом, редакцией и ссылками на официальный реестр.

Каталог отвечает на вопросы "что действует" и "чем заменено". Тексты норм здесь не хранятся: открывайте первоисточник по ссылке из карточки. Статус ставится только по официальному источнику; сомнительный статус помечается как не проверенный, а не как действующий.

## Структура

```text
catalog/ru/       документы, действующие только в России
catalog/kz/       документы, действующие только в Казахстане
catalog/both/     межгосударственные документы, применяемые в обеих странах
docs/             методика ведения каталога и подборки по разделам
scripts/          проверка, сборка индекса, сверка статусов, поиск
_schema.md        описание полей карточки
```

Каталог `catalog/README.md` и индекс `catalog/index.json` собираются из карточек командой `python3 scripts/build_index.py`. Вручную их не правят.

## Быстрый старт

```bash
python3 -m pip install -r requirements.txt
python3 scripts/find.py 60.13330
python3 scripts/find.py "отопление" --jurisdiction kz
python3 scripts/find.py --scope vk --jurisdiction ru
python3 scripts/validate.py
python3 scripts/build_index.py
```

По умолчанию поиск скрывает заменённые документы. Флаг `--all` показывает все.

Проверка доступности ссылок: `python3 scripts/validate.py --links`. Ссылки на `docs.cntd.ru` не опрашиваются автоматически: сайт блокирует запросы из CI, поэтому они показываются как непроверенные, а не как мёртвые.

Сверка статусов с реестрами ничего не меняет в карточках, только печатает расхождения:

```bash
python3 scripts/check_status.py --jurisdiction kz
python3 scripts/check_status.py --id sp-60.13330.2020
```

Подробный регламент - в [docs/maintenance.md](docs/maintenance.md), готовые подборки по разделам - в [docs/topics.md](docs/topics.md).

## Как добавить документ

1. Возьмите статус из официального реестра, а не из поисковой выдачи.
2. Создайте YAML в нужном каталоге по [_schema.md](_schema.md).
3. Запустите `python3 scripts/validate.py` и `python3 scripts/build_index.py`.
4. Проверьте, что в `catalog/README.md` появилась верная строка.

## Ограничения

- Хранятся только реквизиты и ссылки, не тексты документов.
- Дата последней сверки карточки - поле `updated`. Если оно старое, статус мог измениться.
- Каталог покрывает инженерные разделы проектирования и смежные документы, не всю нормативную базу строительства.

## Лицензия

MIT для скриптов каталога, см. [LICENSE](LICENSE). Тексты нормативных документов остаются собственностью их правообладателей и по ссылкам из карточек не копируются.

---

# Catalog of design norms for building engineering systems

A reference for current construction and engineering norms in Russia and Kazakhstan: GOST, SP, SNiP, SN RK, SP RK, NTP RK, ST RK. One document is one YAML card with its status, edition and a link to an official registry.

The catalog answers "what is in force" and "what replaced it". It does not store the texts of the norms: open the source linked from the card. A status is set only from an official source; an unconfirmed status is marked as unchecked rather than as active.

## Layout

```text
catalog/ru/       documents applied only in Russia
catalog/kz/       documents applied only in Kazakhstan
catalog/both/     interstate documents applied in both countries
docs/             maintenance rules and topic guides
scripts/          validation, index build, status check, search
_schema.md        card field reference
```

`catalog/README.md` and `catalog/index.json` are generated from the cards by `python3 scripts/build_index.py`. Do not edit them by hand.

## Quickstart

```bash
python3 -m pip install -r requirements.txt
python3 scripts/find.py 60.13330
python3 scripts/find.py 4.02-01 --jurisdiction kz
python3 scripts/find.py --scope vk --jurisdiction ru
python3 scripts/validate.py
python3 scripts/build_index.py
```

Search hides superseded documents by default. Add `--all` to include them.

Link check: `python3 scripts/validate.py --links`. Links to `docs.cntd.ru` are not probed: the site blocks CI requests, so they are reported as unchecked, not dead.

The status check never edits cards, it only prints discrepancies:

```bash
python3 scripts/check_status.py --jurisdiction kz
python3 scripts/check_status.py --id sp-60.13330.2020
```

See [docs/maintenance.md](docs/maintenance.md) for the maintenance rules and [docs/topics.md](docs/topics.md) for ready-made topic lists.

## Adding a document

1. Take the status from an official registry, not from a search result.
2. Create a YAML card in the right directory following [_schema.md](_schema.md).
3. Run `python3 scripts/validate.py` and `python3 scripts/build_index.py`.
4. Check that the new row in `catalog/README.md` points to the right file.

## Limitations

- Only metadata and links are stored, not the texts of the norms.
- `updated` is the date the card was last checked. If it is old, the status may have changed.
- The catalog covers building engineering design and related documents, not the whole construction code base.

## License

MIT for the catalog scripts, see [LICENSE](LICENSE). Normative documents remain the property of their publishers and are not copied through the links in the cards.
