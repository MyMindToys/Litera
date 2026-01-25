# -*- coding: utf-8 -*-
"""
Пошаговая диагностика парсинга: что было найдено и что нет.
Используется на странице /reference/<id>/errors/ при неудачном парсинге.
"""

import re

from .utils import clean_reference_line

DASH_CLASS = r"[-\u2013\u2014]"


def _step(step: str, found: bool, value: str = "", detail: str = "") -> dict:
    return {"step": step, "found": found, "value": value or "", "detail": detail or ""}


def _diagnose_online(value: str) -> list:
    steps = []
    # 1. Пометка [Электронный ресурс]
    m = re.search(r"\[Электронный\s+ресурс\]", value, re.IGNORECASE)
    steps.append(_step("Пометка [Электронный ресурс]", bool(m), m.group(0) if m else "", "Необязательно."))

    # 2. URL: или Режим доступа:
    m1 = re.search(r"URL:\s*(\S+)", value, re.IGNORECASE)
    m2 = re.search(r"Режим\s+доступа\s*:\s*(\S+)", value, re.IGNORECASE)
    if m1:
        steps.append(_step("URL: или Режим доступа:", True, m1.group(1).rstrip(").,")[:50] + ("…" if len(m1.group(1)) > 50 else ""), "Найден URL:."))
    elif m2:
        steps.append(_step("URL: или Режим доступа:", True, m2.group(1).rstrip(").,")[:50] + ("…" if len(m2.group(1)) > 50 else ""), "Найден Режим доступа:."))
    else:
        steps.append(_step("URL: или Режим доступа:", False, "", "Для сетевого ресурса нужен URL: или Режим доступа:."))

    # 3. Блок « – Место : Издательство, Год» (для физ. носителя без URL)
    m_pub = re.search(r"(?:\.\s*)?[\u2013\u2014]\s*([^:]+?)\s*:\s*([^,]+),\s*(\d{4})", value)
    if m1 or m2:
        steps.append(_step("Блок « – Место : Издательство, Год»", True, "", "Не требуется при наличии URL (сетевой ресурс)."))
    elif m_pub:
        steps.append(_step("Блок « – Место : Издательство, Год»", True, f"{m_pub.group(1).strip()} : {m_pub.group(2).strip()}, {m_pub.group(3)}", "Нужен для ресурса на физ. носителе (CD-ROM) без URL."))
    else:
        steps.append(_step("Блок « – Место : Издательство, Год»", False, "", "Для CD-ROM без URL нужен блок после тире (– или —), напр.: Москва : 1С, 2017."))

    # 4. В шапке «Заглавие / свед. об отв.» (для физ. носителя)
    if m_pub and not (m1 or m2):
        head = value[: m_pub.start()].strip()
        has_slash = " / " in head
        steps.append(_step("В начале: «Заглавие / свед. об отв.»", has_slash, head[:60] + ("…" if len(head) > 60 else "") if head else "", "Разделитель « / » между заглавием и ответственностью."))

    # 5. Носитель (1 CD-ROM и т.п.) — только если ветка физ. носителя
    if m_pub and not (m1 or m2):
        tail = value[m_pub.end() :]
        m_c = re.search(r"\d+\s*(?:СD-ROM|CD-ROM|DVD-ROM?|электрон\.\s*опт\.\s*диск)", tail, re.IGNORECASE)
        steps.append(_step("Сведения о носителе (1 CD-ROM и т.п.)", bool(m_c), m_c.group(0) if m_c else "", "Ищутся в части после «Место : Изд., Год»."))

    return steps


def _diagnose_online_journal(value: str) -> list:
    steps = []
    # 1. « — Режим доступа: » — обязательный разрез
    split = re.split(r"\s+[-\u2013\u2014]\s+Режим\s+доступа\s*:\s*", value, maxsplit=1, flags=re.IGNORECASE)
    if len(split) == 2:
        steps.append(_step("« – Режим доступа: » (разделитель)", True, "Режим доступа:…", ""))
        tail = split[1].strip()
        m_url = re.match(r"(\S+)", tail)
        steps.append(_step("URL после «Режим доступа:»", bool(m_url), (m_url.group(1)[:50] + "…") if m_url and len(m_url.group(1)) > 50 else (m_url.group(1) if m_url else ""), ""))
    else:
        steps.append(_step("« – Режим доступа: » (разделитель)", False, "", "Ожидается: … – Режим доступа: URL …"))

    # 2. Заголовок: «… [Электронный ресурс]: Заглавие»
    m = re.match(r"^(.+?)\s*\[Электронный\s+ресурс\]\s*:\s*(.+)$", split[0] if len(split) >= 1 else "", re.IGNORECASE)
    steps.append(_step("«Основное заглавие [Электронный ресурс]: Заглавие»", bool(m), m.group(0)[:70] + "…" if m and len(m.group(0)) > 70 else (m.group(0) if m else ""), ""))

    return steps


def _diagnose_book(value: str) -> list:
    steps = []
    # 1. Разделение по « . – » или « – » (области)
    parts = [p.strip() for p in re.split(r"\.\s+" + DASH_CLASS + r"\s+", value, maxsplit=2)]
    if len(parts) < 2:
        parts = [p.strip() for p in re.split(r"\s+" + DASH_CLASS + r"\s+", value, maxsplit=2)]
    if len(parts) < 2:
        m = re.search(r"([^:]+)\s*:\s*([^,]+)\s*,\s*(\d{4})", value)
        if m:
            parts = [value[: m.start()].strip(), m.group(0), value[m.end() :].strip()]

    if len(parts) >= 2:
        steps.append(_step("Разделение на области (« . – » или « – »)", True, f"областей: {len(parts)}", ""))
        head, publish_part = parts[0], parts[1]
    else:
        steps.append(_step("Разделение на области (« . – » или « – »)", False, "", "Ожидаются области: шапка, «Место : Изд., Год», хвост (N с.)."))
        return steps

    # 2. В шапке: «Автор. Остальное» (Фамилия, И. О. или Х. О. )
    m = re.match(r"^(.+,\s*[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(.+)$", head)
    if not m:
        m = re.match(r"^(.+?)\.\s*(.+)$", head)
    if m:
        steps.append(_step("В шапке: «Автор. Заглавие [ / свед. об отв.]»", True, m.group(1)[:40] + "…" if len(m.group(1)) > 40 else m.group(1), "Автор до точки, далее заглавие."))
    else:
        steps.append(_step("В шапке: «Автор. Заглавие [ / свед. об отв.]»", False, "", "Ожидается «Фамилия, И. О. Заглавие» или «Автор. Остальное»."))

    # 3. «Место : Издательство, Год»
    m_pub = re.match(r"([^:]+)\s*:\s*([^,]+)\s*,\s*(\d{4})", publish_part)
    if not m_pub and len(parts) > 2:
        m_pub = re.search(r"([^:]+)\s*:\s*([^,]+)\s*,\s*(\d{4})", parts[2])
    if m_pub:
        steps.append(_step("«Место : Издательство, Год»", True, f"{m_pub.group(1).strip()} : {m_pub.group(2).strip()}, {m_pub.group(3)}", ""))
    else:
        steps.append(_step("«Место : Издательство, Год»", False, "", "Напр.: Москва : БХВ, 2020."))

    # 4. «N с.» (страницы)
    tail = parts[2] if len(parts) > 2 else publish_part
    m_p = re.search(r"(\d+)\s*с\.?", tail or publish_part)
    steps.append(_step("Объём «N с.»", bool(m_p), m_p.group(0) if m_p else "", "Количество страниц."))

    return steps


def _diagnose_article_journal(value: str) -> list:
    steps = []
    # 1. « // » (статья // журнал)
    if "//" not in value:
        steps.append(_step("Разделитель « // » (статья // журнал)", False, "", "Обязателен между статьёй и названием журнала."))
        return steps
    steps.append(_step("Разделитель « // » (статья // журнал)", True, "", ""))

    art, rest = value.split("//", 1)
    art, rest = art.strip(), rest.strip()

    # 2. В статье: «Автор. Заглавие»
    m = re.match(r"^(.+,\s*[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(.+)$", art)
    if not m:
        m = re.match(r"^(.+?)\.\s*(.+)$", art)
    steps.append(_step("В части статьи: «Автор. Заглавие»", bool(m), (m.group(1)[:30] + "…") if m else "", ""))

    # 3. Год (19xx/20xx) после « – »
    m_y = re.search(r"(?:[\u002d\u2013\u2014]\s*)(19\d{2}|20\d{2})(?=\s*[\u002d\u2013\u2014]|\s+Т\.|\s+С\.|\.|$)", rest)
    if not m_y:
        m_y = re.search(r"(?:[\u002d\u2013\u2014]\s*)(\d{4})(?=\s*[\u002d\u2013\u2014]|\s+Т\.|\s+С\.|\.|$)", rest)
    steps.append(_step("Год после « – »", bool(m_y), m_y.group(1) if m_y else "", "Напр.: – 2024 –"))

    # 4. Страницы С. X–Y
    m_p = re.search(r"(?:С\.|P\.)\s*(\d+[\u002d\u2013\u2014]?\d*|\d+)", rest, re.IGNORECASE)
    steps.append(_step("Страницы «С. X–Y»", bool(m_p), m_p.group(0) if m_p else "", ""))

    return steps


def _diagnose_article_proceedings(value: str) -> list:
    steps = []
    if " // " not in value:
        steps.append(_step("Разделитель « // » (статья // сборник)", False, "", "Обязателен."))
        return steps
    steps.append(_step("Разделитель « // » (статья // сборник)", True, "", ""))

    art, coll = value.split(" // ", 1)
    art, coll = art.strip(), coll.strip()

    m = re.match(r"^(.+?)\.\s*(.+)$", art)
    steps.append(_step("В части статьи: «Автор. Заглавие»", bool(m), (m.group(1)[:30] + "…") if m else "", ""))

    m_py = re.search(r"([А-Яа-яA-Za-z\-\.\s]+),\s*(\d{4})", coll)
    steps.append(_step("«Место, Год» в части сборника", bool(m_py), f"{m_py.group(1).strip()}, {m_py.group(2)}" if m_py else "", ""))

    m_p = re.search(r"(?:С\.|P\.)\s*(\d+[-\u2013\u2014]?\d*|\d+)", coll, re.IGNORECASE)
    steps.append(_step("Страницы «С. X–Y»", bool(m_p), m_p.group(0) if m_p else "", ""))

    return steps


def _diagnose_dissertation(value: str) -> list:
    steps = []
    m = re.search(r"дис\.\s*[^.]+", value, re.IGNORECASE)
    steps.append(_step("Пометка «дис. … канд./д-ра …»", bool(m), m.group(0) if m else "", ""))

    m = re.search(r"([А-Яа-яA-Za-z\-\.\s]+),\s*(\d{4})", value)
    steps.append(_step("«Место, Год»", bool(m), f"{m.group(1).strip()}, {m.group(2)}" if m else "", ""))

    return steps


def _diagnose_standard(value: str) -> list:
    steps = []
    m = re.search(r"^([^.]+)\.\s+([^.]+)\.\s*", value)
    steps.append(_step("«Обозначение. Основной заголовок.»", bool(m), (m.group(0)[:50] + "…") if m and len(m.group(0)) > 50 else (m.group(0) if m else ""), "Напр.: ГОСТ Р 7.0.100–2018. Система стандартов…"))

    m = re.search(r"([^:]+)\s*:\s*([^,]+),\s*(\d{4})", value)
    steps.append(_step("«Место : Издательство, Год»", bool(m), f"{m.group(1).strip()} : {m.group(2).strip()}, {m.group(3)}" if m else "", ""))

    return steps


def _diagnose_patent(value: str) -> list:
    steps = []
    m = re.search(r"Пат\.\s*[^.]+\.[^/]+/\s*[^;]+", value, re.IGNORECASE)
    steps.append(_step("«Пат. … Название / Изобретатели;»", bool(m), (m.group(0)[:60] + "…") if m and len(m.group(0)) > 60 else (m.group(0) if m else ""), ""))

    return steps


_DIAGNOSTICS = {
    "BOOK": _diagnose_book,
    "ARTICLE_JOURNAL": _diagnose_article_journal,
    "ARTICLE_PROCEEDINGS": _diagnose_article_proceedings,
    "ONLINE": _diagnose_online,
    "ONLINE_JOURNAL": _diagnose_online_journal,
    "DISSERTATION": _diagnose_dissertation,
    "STANDARD": _diagnose_standard,
    "PATENT": _diagnose_patent,
}


def get_parse_diagnostic(raw_text: str, type_code: str) -> list:
    """
    Возвращает пошаговый «ход парсинга»: что найдено, что нет.
    Используется на странице ошибок, когда парсинг не удался (или для отладки).

    :param raw_text: исходный текст ссылки
    :param type_code: код типа (BOOK, ONLINE, ARTICLE_JOURNAL и т.п.)
    :return: список dict с ключами step, found, value, detail
    """
    value = clean_reference_line(raw_text or "")
    if not value:
        return [_step("Исходный текст после очистки", False, "", "Строка пуста или не содержит букв.")]

    fn = _DIAGNOSTICS.get(type_code)
    if not fn:
        return [_step("Тип «{}»".format(type_code), True, "", "Диагностика по шагам для этого типа не реализована.")]

    return fn(value)
