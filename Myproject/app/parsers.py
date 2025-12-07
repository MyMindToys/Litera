import re

from .models import Reference, ReferenceType
from .utils import clean_reference_line


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
    (?P<journal_title>.+?)\.\s+                              # название журнала
    (?P<year>\d{4})\.\s*                                     # год
    (?:Т\.\s*(?P<volume>\d+),\s*)?                           # том (необязательно)
    №\s*(?P<issue>.+?)\.\s*                                  # номер
    (?:С\.\s*)?(?P<pages>.+?)(?:\.|$)                        # страницы
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
    
    # 1. Делим на части по " . — " (границы областей)
    # Примеры:
    #   "... Бруттан. — Псков : ПсковГУ, 2025. — 134 с. — ISBN ..."
    #   "... Python. — Москва : БХВ-Петербург, 2017. — 352 с."
    parts = [p.strip() for p in re.split(r"\.\s+[—-]\s+", value, maxsplit=2)]
    
    if len(parts) < 2:
        return {}  # не похоже на книгу
    
    head = parts[0]          # авторы + заглавие + возможные сведения об издании/ответственности
    publish_part = parts[1]  # "Псков : ПсковГУ, 2025" / "Москва : БХВ-Петербург, 2017"
    tail = parts[2] if len(parts) > 2 else ""  # "134 с. — ISBN ..." / "352 с."
    
    # 2. В "шапке" отделяем авторов от остального: до первой точки — авторы
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
    
    # 5. Область выхода в свет: "Место : Издательство, 2017"
    m_pub = re.match(r"(?P<place>[^:]+)\s*:\s*(?P<publisher>[^,]+)\s*,\s*(?P<year>\d{4})", publish_part)
    if not m_pub:
        return {}
    
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
    """Парсинг ссылки типа 'Статья из журнала'"""
    text = clean_reference_line(text or "")
    match = ARTICLE_JOURNAL_PATTERN.match(text)
    if match:
        result = match.groupdict()
        return {k: v.strip() if v else "" for k, v in result.items()}
    return {}


def parse_article_proceedings(text: str) -> dict:
    """Парсинг ссылки типа 'Статья из сборника/конференции'"""
    text = clean_reference_line(text or "")
    match = ARTICLE_PROCEEDINGS_PATTERN.match(text)
    if match:
        result = match.groupdict()
        return {k: v.strip() if v else "" for k, v in result.items()}
    return {}


def parse_online(text: str) -> dict:
    """
    Разбор электронного ресурса вида:
    Организация/автор. Заглавие. [Доп. сведения, дата выхода.] URL: ... (дата обращения: 26.09.2025).
    или
    Организация/автор. Заглавие [Электронный ресурс]. — Режим доступа: https://...
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
    
    # Вариант 1: "URL: https://..."
    m_url1 = re.search(r"URL:\s*(?P<url>\S+)", value, flags=re.IGNORECASE)
    if m_url1:
        url = m_url1.group("url").rstrip(").,")
        url_start = m_url1.start()
        url_end = m_url1.end()
        url_label_text = "URL:"
        result["url_label"] = "URL:"
    
    # Вариант 2: "— Режим доступа: https://..." или "Режим доступа: https://..."
    if not url:
        m_url2 = re.search(r"([—-]\s*)?Режим\s+доступа\s*:\s*(?P<url>\S+)", value, flags=re.IGNORECASE)
        if m_url2:
            url = m_url2.group("url").rstrip(").,")
            url_start = m_url2.start()
            url_end = m_url2.end()
            # Извлекаем полную метку "Режим доступа:" или "— Режим доступа:"
            # Ищем начало метки до URL
            label_start = m_url2.start()
            # Ищем "Режим доступа:" в найденном совпадении
            label_full_match = m_url2.group(0)
            # Извлекаем только метку без URL
            label_match = re.match(r"([—-]\s*)?Режим\s+доступа\s*:", label_full_match, flags=re.IGNORECASE)
            if label_match:
                url_label_text = label_match.group(0).strip()
            else:
                url_label_text = "Режим доступа:"
            result["url_label"] = url_label_text
    
    if not url:
        return {}
    
    result["url"] = url
    
    before_url = value[:url_start].strip() if url_start else ""
    after_url = value[url_end:].strip() if url_end else ""
    
    # 3. Дата обращения в "хвосте" после URL
    m_access = re.search(
        r"дата\s+обращения\s*:\s*(?P<date>\d{2}\.\d{2}\.\d{4})",
        after_url,
        flags=re.IGNORECASE,
    )
    if m_access:
        result["access_date"] = m_access.group("date").strip()
    
    # 4. Пытаемся вытащить дату публикации (если есть) в части до URL
    # Например: "... 30.05.2025. URL: ..."
    m_pub = re.search(r"(?P<date_pub>\d{2}\.\d{2}\.\d{4})", before_url)
    if m_pub:
        result["date_pub"] = m_pub.group("date_pub").strip()
        title_part = before_url[:m_pub.start()].strip().rstrip(".")
    else:
        title_part = before_url.rstrip(" .")
    
    # 5. Удаляем пометку [Электронный ресурс] из title_part, если она там есть
    title_part = re.sub(r"\[Электронный\s+ресурс\]", "", title_part, flags=re.IGNORECASE).strip()
    
    # 6. Делим начало на "автор/организация" и заглавие по первой точке или двоеточию
    # Примеры:
    #   "SAP SE. Manufacturing Master Data of Production Orders. SAP Help Portal"
    #   "APQC. APQC's Process Classification Framework (PCF): ..."
    #   "Metanit: руководство по Python и Django"
    if ":" in title_part and "." not in title_part[:title_part.find(":")]:
        # Если есть двоеточие и нет точки до него, делим по двоеточию
        parts = [p.strip() for p in title_part.split(":", 1)]
        if len(parts) == 2:
            result["authors"] = parts[0]
            result["title"] = parts[1]
        else:
            result["title"] = title_part
    else:
        # Делим по первой точке
        parts = [p.strip() for p in title_part.split(".", 1)]
        if len(parts) == 2:
            result["authors"] = parts[0]
            result["title"] = parts[1]
        else:
            # если нет точки, считаем всё заглавием
            result["title"] = title_part
    
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
    split = re.split(r"\s+[—-]\s+Режим\s+доступа\s*:\s*", value, maxsplit=1, flags=re.IGNORECASE)
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

