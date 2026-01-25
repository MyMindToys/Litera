import re

from .models import Reference, ReferenceType
from .utils import clean_reference_line

# Класс символов тире (дефис, en-dash –, em-dash —) для разделителей областей по ГОСТ
DASH_CLASS = r"[-\u2013\u2014]"

# Регулярные выражения для парсинга библиографических ссылок

BOOK_PATTERN = re.compile(
    r"""
    ^(?P<authors>.+?)\.\s+                                   # авторы до первой точки
    (?P<title>.+?)\s*:\s*                                    # заглавие до двоеточия
    (?P<document_type>[^.]+)?\.?\s*                          # тип документа (необязательно)
    (?P<edition>[^.]+)?\.?\s*                                # сведения об издании (необязательно)
    (?P<place>[^:]+)\s*:\s*                                  # место издания до двоеточия
    (?P<publisher>[^,]+),\s*                                 # издательство до запятой
    (?P<year>\d{4})\.\s*                                     # год
    (?P<pages>.+?)(?:\.|$)                                    # количество страниц
    """,
    re.VERBOSE,
)

ARTICLE_JOURNAL_PATTERN = re.compile(
    r"""
    ^(?P<authors>.+?)\.\s+                                   # авторы
    (?P<title>.+?)\s+//\s+                                   # заглавие статьи
    (?P<journal_title>.+?)\s*\.\s*(?=[-\u2013\u2014]?\s*\d{4})          # журнал до " . " или " . – " перед годом
    \s*(?:[-\u2013\u2014]\s*)?(?P<year>\d{4})\.?\s*                     # год
    (?:[-\u2013\u2014]\s*)?                                             # необяз. " – "
    (?:Т\.\s*(?P<volume>\d+)(?:\s*,\s*вып\.\s*\d+)?\.\s*(?:[-\u2013\u2014]\s*)?)?  # том (необяз.)
    (?:№\s*(?P<issue>[^.–]+?)\.\s*(?:[-\u2013\u2014]\s*)?)?            # номер (необяз.)
    (?:С\.|P\.)?\s*(?P<pages>.+?)(?:\.|$)                    # страницы
    """,
    re.VERBOSE,
)

ARTICLE_PROCEEDINGS_PATTERN = re.compile(
    r"""
    ^(?P<authors>.+?)\.\s+                                   # авторы
    (?P<title>.+?)\s+//\s+                                   # заглавие статьи
    (?P<collection_title>.+?)\s*:\s*                         # название сборника
    (?P<collection_subtitle>[^.]+)?\.?\s*                    # подзаголовок (необязательно)
    (?P<place>[^,]+),\s*                                     # место
    (?P<year>\d{4})\.\s*                                     # год
    (?:С\.\s*)?(?P<pages>.+?)(?:\.|$)                        # страницы
    """,
    re.VERBOSE,
)

ONLINE_PATTERN = re.compile(
    r"""
    ^(?P<title>.+?)\s+
    \[Электронный\s+ресурс\]\.\s*                            # пометка ресурса
    .*?URL:\s*(?P<url>\S+).*?                                # URL
    (?:\(дата\s+обращения:\s*(?P<access_date>[^)]+)\))?     # дата обращения (необязательно)
    """,
    re.VERBOSE | re.IGNORECASE,
)

DISSERTATION_PATTERN = re.compile(
    r"""
    ^(?P<author>.+?)\.\s+                                    # автор
    (?P<title>.+?)\s*:\s*                                    # заглавие
    (?P<dissertation_mark>дис\.[^.]+)\.\s*                    # пометка диссертации
    (?P<place>[^,]+),\s*                                     # место
    (?P<year>\d{4})\.\s*                                     # год
    (?P<pages>.+?)(?:\.|$)                                    # страницы
    """,
    re.VERBOSE | re.IGNORECASE,
)

STANDARD_PATTERN = re.compile(
    r"""
    ^(?P<doc_code>[^.]+)\.\s+                                # ГОСТ / закон
    (?P<title_main>[^.]+)\.\s*                               # основной заголовок
    (?P<title_sub>[^.]+)?\.?\s*                              # доп. заголовок (может отсутствовать)
    (?P<place>[^:]+)\s*:\s*                                  # место
    (?P<publisher>[^,]+),\s*                                 # издательство
    (?P<year>\d{4})\.\s*                                     # год
    (?P<pages>.+?)(?:\.|$)                                    # страницы
    """,
    re.VERBOSE,
)

PATENT_PATTERN = re.compile(
    r"""
    ^(?P<patent_mark>Пат\.\s*[^.]+)\.\s*                     # обозначение патента
    (?P<title>.+?)\s*/\s*                                    # название изобретения
    (?P<inventors>[^;]+);?\s*                                # изобретатели
    (?P<owner_info>[^.]+)?\.?\s*                             # правообладатель (необязательно)
    (?:Заявл\.\s*(?P<application_date>[^;]+);)?\s*           # дата заявки (необязательно)
    (?:опубл\.\s*(?P<publication_date>[^,]+),\s*             # дата публикации (необязательно)
    (?P<bulletin>Бюл\.\s*№\s*\d+))?                           # бюллетень (необязательно)
    """,
    re.VERBOSE | re.IGNORECASE,
)


# Функции парсинга по типам

def parse_book(text: str) -> dict:
    """
    Разбор печатной книги по ГОСТ Р 7.0.100–2018 (монографического типа):
    Автор(ы). Заглавие [: сведения об издании] [/ сведения об ответственности]. — Место : Издательство, Год. — Страницы [хвост игнорируем].
    """
    if not text:
        return {}
    
    value = clean_reference_line(text)
    
    result = {
        "authors": "",
        "title": "",
        "document_type": "",
        "responsibility": "",
        "place": "",
        "publisher": "",
        "year": "",
        "pages": "",
    }
    
    # 1. Делим на части по " . — " или " – " (границы областей по ГОСТ)
    # Примеры:
    #   "... Бруттан. — Псков : ПсковГУ, 2025. — 134 с. — ISBN ..."
    #   "... Python. — Москва : БХВ-Петербург, 2017. — 352 с."
    #   "... / Автор. – Москва : Изд-во, 2010. – 212 с."
    parts = [p.strip() for p in re.split(r"\.\s+" + DASH_CLASS + r"\s+", value, maxsplit=2)]
    
    if len(parts) < 2:
        # Fallback: разделитель только " – " без точки перед ним
        parts = [p.strip() for p in re.split(r"\s+" + DASH_CLASS + r"\s+", value, maxsplit=2)]
    if len(parts) < 2:
        # Fallback: ищем "Место : Издательство, Год" в строке
        m_pub = re.search(r"([^:]+)\s*:\s*([^,]+)\s*,\s*(\d{4})(?:\.|$|\s+" + DASH_CLASS + r"|\s+\d+\s*с\.?)", value)
        if m_pub:
            head = value[: m_pub.start()].strip().rstrip(".,")
            publish_part = m_pub.group(0).rstrip(".,")
            tail = value[m_pub.end() :].strip()
            parts = [head, publish_part, tail]
    if len(parts) < 2:
        return {}
    
    head = parts[0]          # авторы + заглавие + возможные сведения об издании/ответственности
    publish_part = parts[1]  # "Псков : ПсковГУ, 2025" / "Москва : БХВ-Петербург, 2017"
    tail = parts[2] if len(parts) > 2 else ""  # "134 с. — ISBN ..." / "352 с."
    
    # 2. В "шапке" отделяем авторов от остального.
    # Приоритет: "Фамилия, И. О." (инициалы с точками не режем) — иначе до первой " . ".
    m_auth = re.match(
        r"^(?P<authors>.+,\s*[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(?P<rest>.+)$",
        head,
    )
    if not m_auth:
        m_auth = re.match(r"(?P<authors>.+?)\.\s*(?P<rest>.+)", head)
    if not m_auth:
        return {}
    
    result["authors"] = m_auth.group("authors").strip()
    rest = m_auth.group("rest").strip()
    
    # 3. В "rest" отделяем сведения об ответственности по " / "
    responsibility = ""
    if " / " in rest:
        before_slash, responsibility = rest.split(" / ", 1)
        responsibility = responsibility.strip()
    else:
        before_slash = rest
    
    result["responsibility"] = responsibility
    
    # 4. В before_slash отделяем документный тип по ":" только если после двоеточия идут ключевые слова
    # (монография, учебник, учеб. пособие, практикум, справочник, курс лекций, пособие)
    doc_type_pattern = re.compile(
        r"^\s*(?P<title>.+?)\s*:\s*(?P<doc>(?i:монография|учебник|учеб\.?\s*пособие|практикум|справочник|курс\s+лекций|пособие))\s*$",
        re.IGNORECASE,
    )
    
    m_doc = doc_type_pattern.match(before_slash)
    if m_doc:
        result["title"] = m_doc.group("title").strip()
        result["document_type"] = m_doc.group("doc").strip()
    else:
        # двоеточие (если есть) считаем частью заглавия (как у Дронова)
        result["title"] = before_slash.strip()
    
    # 5. Область выхода в свет: "Место : Издательство, Год" (может быть "Место : Изд1 : Изд2, Год")
    # Если во 2-й области "2-е изд." и т.п., ищем блок выхода в 3-й: "Москва : Флинта : Наука, 2009 – 396 с."
    m_pub = re.match(r"(?P<place>[^:]+)\s*:\s*(?P<publisher>[^,]+)\s*,\s*(?P<year>\d{4})", publish_part)
    if not m_pub and tail:
        # Во 2-й области "2-е изд." и т.п.; ищем "Место : Издательство, Год" в tail
        m = re.search(r"([^:]+)\s*:\s*([^,]+)\s*,\s*(\d{4})(?:\.|$|\s+" + DASH_CLASS + r"|\s+\d+\s*с\.?)", tail)
        if m:
            result["place"] = m.group(1).strip()
            result["publisher"] = m.group(2).strip()
            result["year"] = m.group(3).strip()
            tail = tail[m.end() :].strip()  # " – 396 с. – ISBN..." для страниц
        else:
            return {}
    elif not m_pub:
        return {}
    else:
        result["place"] = m_pub.group("place").strip()
        result["publisher"] = m_pub.group("publisher").strip()
        result["year"] = m_pub.group("year").strip()
    
    # 6. Область физической характеристики: ищем "число с." в хвосте
    tail_candidate = tail if tail else ""
    pages_match = re.search(r"(?P<pages>\d+)\s*с\.?", tail_candidate)
    if not pages_match:
        # иногда количество страниц может идти сразу после года в publish_part
        pages_match = re.search(r"(?P<pages>\d+)\s*с\.?", publish_part)
    
    if pages_match:
        result["pages"] = pages_match.group("pages").strip()
    
    # Если не нашли страницы — формально книга все равно разобрана, но поле pages пустое.
    return result


def parse_article_journal(text: str) -> dict:
    """
    Парсинг ссылки типа 'Статья из журнала' по ГОСТ Р 7.0.100–2018.
    Поддерживает: Автор. Заглавие [ / свед. об отв.] // Журнал. [Серия: ...] – Год – Т. N, вып. M – С. X–Y.
    """
    value = clean_reference_line(text or "")
    if not value:
        return {}

    result = {
        "authors": "",
        "title": "",
        "journal_title": "",
        "year": "",
        "volume": "",
        "issue": "",
        "pages": "",
    }

    # 1. Строгий шаблон
    match = ARTICLE_JOURNAL_PATTERN.match(value)
    if match:
        return {k: (v or "").strip() for k, v in match.groupdict().items()}

    # 2. Пошаговый разбор: " // " или "//" между статьёй и журналом
    if "//" not in value:
        return {}

    parts = re.split(r"\s*//\s*", value, maxsplit=1)
    if len(parts) != 2:
        return {}
    article_part = parts[0].strip()
    journal_part = parts[1].strip()

    # 3. Статья: "Автор. Заглавие [ / свед. об отв.]"
    m_auth = re.match(
        r"^(?P<authors>.+,\s*[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(?P<rest>.+)$",
        article_part,
    )
    if not m_auth:
        m_auth = re.match(r"^(?P<authors>.+?)\.\s*(?P<rest>.+)$", article_part)
    if not m_auth:
        return {}

    result["authors"] = m_auth.group("authors").strip()
    rest = m_auth.group("rest").strip()
    if " / " in rest:
        result["title"] = rest.split(" / ", 1)[0].strip()
    else:
        result["title"] = rest

    # 4. Журнал: "Название. [Серия: ...] – Год – [Т. N, вып. M] – С. X–Y"
    # Год — после " – " или " . " (чтобы не захватить 1810 из ISSN)
    m_year = re.search(r"(?:[\u002d\u2013\u2014]\s*)(?P<year>19\d{2}|20\d{2})(?=\s*[\u002d\u2013\u2014]|\s+Т\.|\s+С\.|\.|$)", journal_part)
    if not m_year:
        m_year = re.search(r"(?:[\u002d\u2013\u2014]\s*)(?P<year>\d{4})(?=\s*[\u002d\u2013\u2014]|\s+Т\.|\s+С\.|\.|$)", journal_part)
    if not m_year:
        m_year = re.search(r"(?:\.\s+)(?P<year>19\d{2}|20\d{2})(?=\s*\.|\s+Т\.|\s+№|\s+С\.|$)", journal_part)
    if not m_year:
        m_year = re.search(r"(?:\.\s+)(?P<year>\d{4})(?=\s*\.|\s+Т\.|\s+№|\s+С\.|$)", journal_part)

    if m_year:
        result["year"] = m_year.group("year").strip()
        year_start = m_year.start()
        pre = journal_part[:year_start].rstrip()
    else:
        # Год не найден (ссылку могли обрезать) — всё равно извлекаем журнал, год/страницы уйдут в «Обнаруженные проблемы»
        result["year"] = ""
        year_start = len(journal_part)
        pre = journal_part

    pre = re.sub(r"[\s.\u002d\u2013\u2014]+$", "", pre)
    result["journal_title"] = pre.strip().rstrip(".,")

    # Том и вып. после года: " – Т. 27, вып. 2 – " или " – Т. 27 – " или " – Вып. 2 – "
    m_vol = re.search(r"Т\.\s*(?P<volume>\d+)", journal_part)
    if m_vol:
        result["volume"] = m_vol.group("volume").strip()
    m_vypp = re.search(r"вып\.\s*(?P<issue>\d+)", journal_part)
    m_num = re.search(r"№\s*(?P<issue>[^." + "\u2013\u2014" + r"\s]+)", journal_part)
    if m_vypp:
        result["issue"] = m_vypp.group("issue").strip()
    elif m_num:
        result["issue"] = m_num.group("issue").strip()

    # Страницы: С. X–Y или P. X–Y
    m_pages = re.search(
        r"(?:С\.|P\.)\s*(?P<pages>\d+[\u002d\u2013\u2014]?\d*|\d+)",
        journal_part,
        re.IGNORECASE,
    )
    if m_pages:
        result["pages"] = m_pages.group("pages").strip()

    return result


def parse_article_proceedings(text: str) -> dict:
    """
    Парсинг ссылки типа 'Статья из сборника/конференции' по ГОСТ Р 7.0.100–2018.
    Поддерживает:
      Автор. Заглавие [ / свед. об отв.] // Название сборника [ : подзаголовок | / орг.]. – Место, Год [ – Вып. N] – С. X–Y.
    """
    value = clean_reference_line(text or "")
    if not value:
        return {}

    result = {
        "authors": "",
        "title": "",
        "collection_title": "",
        "collection_subtitle": "",
        "place": "",
        "year": "",
        "pages": "",
    }

    # 1. Пробуем строгий шаблон (Название : Подзаголовок. Место, Год. С.)
    match = ARTICLE_PROCEEDINGS_PATTERN.match(value)
    if match:
        return {k: (v or "").strip() for k, v in match.groupdict().items()}

    # 2. Пошаговый разбор: обязательное " // " между статьёй и сборником
    if " // " not in value:
        return {}

    article_part, collection_part = value.split(" // ", 1)
    article_part = article_part.strip()
    collection_part = collection_part.strip()

    # 3. Статья: "Автор. Заглавие [ / свед. об отв.]"
    m_auth = re.match(
        r"^(?P<authors>.+,\s*[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(?P<rest>.+)$",
        article_part,
    )
    if not m_auth:
        m_auth = re.match(r"^(?P<authors>.+?)\.\s*(?P<rest>.+)$", article_part)
    if not m_auth:
        return {}

    result["authors"] = m_auth.group("authors").strip()
    rest = m_auth.group("rest").strip()
    if " / " in rest:
        result["title"] = rest.split(" / ", 1)[0].strip()
    else:
        result["title"] = rest

    # 4. Сборник: "Название [ / подзагол. или орг.] . – Место, Год [ – Вып. N] – С. X–Y"
    # Ищем "Место, Год" и "С. X–Y" (или "С. X" или "P. X–Y")
    m_place_year = re.search(
        r"([А-Яа-яA-Za-z\-\.\s]+),\s*(\d{4})",
        collection_part,
    )
    m_pages = re.search(
        r"(?:С\.|P\.)\s*(\d+[-\u2013\u2014]?\d*|\d+)",
        collection_part,
        re.IGNORECASE,
    )

    if not m_place_year:
        return {}

    result["place"] = m_place_year.group(1).strip()
    result["year"] = m_place_year.group(2).strip()

    if m_pages:
        result["pages"] = m_pages.group(1).strip()

    # Название и подзаголовок — часть до " – " перед "Место, Год"
    # Разделитель: " . – " или " – " (тире по ГОСТ)
    tail_before_place = collection_part[: m_place_year.start()].strip()
    # убрать завершающие " . – " или " – "
    tail_before_place = re.sub(r"[.\s]*[\u002d\u2013\u2014]\s*$", "", tail_before_place).strip()

    if " / " in tail_before_place:
        result["collection_title"] = tail_before_place.split(" / ", 1)[0].strip()
        sub = tail_before_place.split(" / ", 1)[1].strip().rstrip(",")
        # при наличии "Вып. N" в collection_part — добавить в подзаголовок
        m_vypp = re.search(r"Вып\.\s*\d+", collection_part)
        if m_vypp:
            sub = (sub + " " + m_vypp.group(0)).strip()
        result["collection_subtitle"] = sub
    else:
        result["collection_title"] = tail_before_place.rstrip(".,")
        m_vypp = re.search(r"Вып\.\s*\d+", collection_part)
        if m_vypp:
            result["collection_subtitle"] = m_vypp.group(0).strip()

    return result


def parse_online(text: str) -> dict:
    """
    Разбор электронного ресурса вида:
    Организация/автор. Заглавие. [Доп. сведения, дата выхода.] URL: ... (дата обращения: 26.09.2025).
    или
    Организация/автор. Заглавие [Электронный ресурс]. — Режим доступа: https://...
    или ресурс на физическом носителе (CD-ROM и т.п.) без URL:
    Заглавие [доп.] / свед. об отв. – Место : Издательство, Год. – 1 CD-ROM. – …
    """
    if not text:
        return {}

    value = clean_reference_line(text)

    result = {
        "authors": "",
        "title": "",
        "date_pub": "",
        "resource_type_mark": "",
        "url_label": "",
        "url": "",
        "access_date": "",
        "place": "",
        "publisher": "",
        "year": "",
        "carrier": "",
    }

    # 1. Ищем пометку ресурса [Электронный ресурс] (если есть)
    m_mark = re.search(r"\[Электронный\s+ресурс\]", value, flags=re.IGNORECASE)
    if m_mark:
        result["resource_type_mark"] = m_mark.group(0)

    # 2. Ищем URL - поддерживаем два варианта:
    #    - "URL: https://..."
    #    - "— Режим доступа: https://..."
    url = None
    url_start = None
    url_end = None
    url_label_text = ""

    # URL: \S+ и, если после "?" в URL идёт пробел и параметры ("? page=book&id=..."), добираем их: \s+[^\s(]+
    _url_re = r"(?P<url>\S+(?:\s+[^\s(]+)?)"
    m_url1 = re.search(r"URL:\s*" + _url_re, value, flags=re.IGNORECASE)
    if m_url1:
        url = m_url1.group("url").rstrip(").,")
        url_start = m_url1.start()
        url_end = m_url1.end()
        url_label_text = "URL:"
        result["url_label"] = "URL:"

    if not url:
        m_url2 = re.search(r"([-\u2013\u2014]\s*)?Режим\s+доступа\s*:\s*" + _url_re, value, flags=re.IGNORECASE)
        if m_url2:
            url = m_url2.group("url").rstrip(").,")
            url_start = m_url2.start()
            url_end = m_url2.end()
            label_full_match = m_url2.group(0)
            label_match = re.match(r"([-\u2013\u2014]\s*)?Режим\s+доступа\s*:", label_full_match, flags=re.IGNORECASE)
            if label_match:
                url_label_text = label_match.group(0).strip()
            else:
                url_label_text = "Режим доступа:"
            result["url_label"] = url_label_text

    if url:
        # ———— Ветка с URL (сетевой ресурс) ————
        result["url"] = url
        before_url = value[:url_start].strip() if url_start else ""
        after_url = value[url_end:].strip() if url_end else ""

        # Извлечь «Место : Издательство, Год» из книжного блока (напр. « . - Новосибирск: Изд., 2018»).
        # Берём тире только с пробелом после (\s+), чтобы не спутать дефис в «бизнес-аналитика».
        m_place = re.search(r"[\-\u2013\u2014]\s+([^:]+?)\s*:\s*([^,]+),\s*(\d{4})", before_url)
        if m_place:
            result["place"] = m_place.group(1).strip()
            result["publisher"] = m_place.group(2).strip()
            result["year"] = m_place.group(3).strip()

        m_access = re.search(
            r"дата\s+обращения\s*:\s*(?P<date>\d{2}\.\d{2}\.\d{4})",
            after_url,
            flags=re.IGNORECASE,
        )
        if m_access:
            result["access_date"] = m_access.group("date").strip()

        m_pub = re.search(r"(?P<date_pub>\d{2}\.\d{2}\.\d{4})", before_url)
        if m_pub:
            result["date_pub"] = m_pub.group("date_pub").strip()
            title_part = before_url[: m_pub.start()].strip().rstrip(".")
        else:
            title_part = before_url.rstrip(" .")

        title_part = re.sub(r"\[Электронный\s+ресурс\]", "", title_part, flags=re.IGNORECASE).strip()

        # Сначала пробуем «Фамилия И. О. Заглавие» (инициалы с точками не режем)
        m_auth = re.match(
            r"^([А-Яа-яA-Za-z\-]+\s+[А-ЯA-Z]\.(?:\s*[А-ЯA-Z]\.)*)\s+(.+)$",
            title_part,
        )
        if m_auth:
            result["authors"] = m_auth.group(1).strip()
            rest = m_auth.group(2).strip()
            # Отрезаем блок « . - Место» / « . – Изд., Год» — до него только заглавие и « :учебное пособие»
            parts = re.split(r"\.\s*[\-\u2013\u2014]\s+", rest, maxsplit=1)
            first = parts[0].strip()
            # Убираем « :учебное пособие», « : учебник» и т.п. с конца
            first = re.sub(
                r"\s*:\s*(учебное\s+пособие|учеб\.\s*пособие|учебник|монография|практикум|справочник|пособие)\s*\.?\s*$",
                "",
                first,
                flags=re.IGNORECASE,
            ).strip()
            result["title"] = first or rest
        else:
            # Старая логика: «Организация: Заглавие» или «Автор. Заглавие»
            if ":" in title_part and "." not in title_part[: title_part.find(":")]:
                parts = [p.strip() for p in title_part.split(":", 1)]
                if len(parts) == 2:
                    result["authors"] = parts[0]
                    result["title"] = parts[1]
                else:
                    result["title"] = title_part
            else:
                parts = [p.strip() for p in title_part.split(".", 1)]
                if len(parts) == 2:
                    result["authors"] = parts[0]
                    result["title"] = parts[1]
                else:
                    result["title"] = title_part

        if result.get("url") and not (result.get("resource_type_mark") or "").strip():
            result["resource_type_mark"] = "[Электронный ресурс]"
        return result

    # ———— Ветка без URL: ресурс на физическом носителе (CD-ROM и т.п.) ————
    # Ищем блок " – Место : Издательство, Год" (после " . – " или " – ").
    # Используем только en/em-dash [\u2013\u2014], чтобы не спутать с дефисом в "КОМПАС-3D".
    m_pub = re.search(
        r"(?:\.\s*)?[\u2013\u2014]\s*([^:]+?)\s*:\s*([^,]+),\s*(\d{4})",
        value,
    )
    if not m_pub:
        return {}

    result["place"] = m_pub.group(1).strip()
    result["publisher"] = m_pub.group(2).strip()
    result["year"] = m_pub.group(3).strip()
    head = value[: m_pub.start()].strip().rstrip(".,")
    tail = value[m_pub.end() :].strip()

    # Заглавие и сведения об ответственности: "Заглавие [доп.] / свед. об отв."
    if " / " in head:
        before_slash, result["authors"] = head.split(" / ", 1)
        result["authors"] = result["authors"].strip()
    else:
        before_slash = head

    title_part = re.sub(r"\[Электронный\s+ресурс\]", "", before_slash, flags=re.IGNORECASE).strip()
    result["title"] = title_part

    if not (result.get("resource_type_mark") or "").strip():
        result["resource_type_mark"] = "[Электронный ресурс]"

    # Носитель в хвосте: "1 CD-ROM", "1 СD-ROM", "1 электрон. опт. диск" и т.п.
    m_carrier = re.search(
        r"(\d+\s*(?:СD-ROM|CD-ROM|DVD-ROM?|электрон\.\s*опт\.\s*диск))\.?",
        tail,
        re.IGNORECASE,
    )
    if m_carrier:
        result["carrier"] = m_carrier.group(1).strip().rstrip(".")

    return result


def parse_online_journal(text: str) -> dict:
    """
    Электронный журнал по ГОСТ Р 7.0.100–2018 (упрощенный вариант):
    Электронный журнал [Электронный ресурс]: Заглавие журнала. — Режим доступа: URL (дата обращения: дд.мм.гггг).
    """
    if not text:
        return {}
    
    value = clean_reference_line(text)
    
    result = {
        "title_main": "",
        "resource_type_mark": "",
        "title_sub": "",
        "access_mode_label": "",
        "url": "",
        "access_date": "",
    }
    
    # 1. Разделяем на часть до "— Режим доступа" и хвост с URL
    split = re.split(r"\s+[-\u2013\u2014]\s+Режим\s+доступа\s*:\s*", value, maxsplit=1, flags=re.IGNORECASE)
    if len(split) != 2:
        return {}
    
    head = split[0].strip()      # "Электронный журнал [Электронный ресурс]: Образовательный комплекс №11, г. Москва."
    tail = split[1].strip()      # "https://... (дата обращения: 23.11.2025)."
    
    # 2. В хвосте ищем URL и дату обращения
    m_url = re.match(r"(?P<url>\S+)", tail)
    if not m_url:
        return {}
    
    result["url"] = m_url.group("url").rstrip(").,")
    
    after_url = tail[m_url.end():].strip()
    
    m_access = re.search(
        r"дата\s+обращения\s*:\s*(?P<date>\d{2}\.\d{2}\.\d{4})",
        after_url,
        flags=re.IGNORECASE,
    )
    if m_access:
        result["access_date"] = m_access.group("date").strip()
    
    result["access_mode_label"] = "Режим доступа:"
    
    # 3. Заголовочная часть: "Электронный журнал [Электронный ресурс]: Образовательный комплекс №11, г. Москва."
    m_head = re.match(
        r"^(?P<title_main>.+?)\s*(?P<mark>\[Электронный\s+ресурс\])\s*:\s*(?P<title_sub>.+)$",
        head,
        flags=re.IGNORECASE,
    )
    if not m_head:
        return {}
    
    result["title_main"] = m_head.group("title_main").strip().rstrip(" .")
    result["resource_type_mark"] = m_head.group("mark").strip()
    result["title_sub"] = m_head.group("title_sub").strip().rstrip(" .")
    
    return result


def parse_dissertation(text: str) -> dict:
    """Парсинг ссылки типа 'Диссертация/автореферат'"""
    text = clean_reference_line(text or "")
    match = DISSERTATION_PATTERN.match(text)
    if match:
        result = match.groupdict()
        return {k: v.strip() if v else "" for k, v in result.items()}
    return {}


def parse_standard(text: str) -> dict:
    """Парсинг ссылки типа 'Нормативный документ'"""
    text = clean_reference_line(text or "")
    match = STANDARD_PATTERN.match(text)
    if match:
        result = match.groupdict()
        return {k: v.strip() if v else "" for k, v in result.items()}
    return {}


def parse_patent(text: str) -> dict:
    """Парсинг ссылки типа 'Патент'"""
    text = clean_reference_line(text or "")
    match = PATENT_PATTERN.match(text)
    if match:
        result = match.groupdict()
        return {k: v.strip() if v else "" for k, v in result.items()}
    return {}


# Словарь соответствий кода типа и функции парсинга
PARSERS_BY_TYPE = {
    "BOOK": parse_book,
    "ARTICLE_JOURNAL": parse_article_journal,
    "ARTICLE_PROCEEDINGS": parse_article_proceedings,
    "ONLINE": parse_online,
    "ONLINE_JOURNAL": parse_online_journal,
    "DISSERTATION": parse_dissertation,
    "STANDARD": parse_standard,
    "PATENT": parse_patent,
}


def parse_reference_instance(reference: Reference) -> dict:
    """
    Парсит одну ссылку в зависимости от reference.reference_type.
    Возвращает словарь полей (или пустой словарь, если парсинг не удался).
    Никаких изменений в базе здесь не выполняется.
    
    Args:
        reference: Экземпляр модели Reference
        
    Returns:
        dict: Словарь с распарсенными полями, где ключи соответствуют
              именам полей из ReferenceField.name
    """
    if reference.reference_type is None:
        return {}

    type_code = reference.reference_type.code
    parser = PARSERS_BY_TYPE.get(type_code)
    if parser is None:
        return {}

    text = reference.raw_text or ""
    return parser(text)
