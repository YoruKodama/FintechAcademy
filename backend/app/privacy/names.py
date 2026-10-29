"""Словарь русских имён и признаки фамилий и отчеств для обезличивания ФИО."""

import re

_MALE = """
Александр Алексей Анатолий Андрей Антон Аркадий Арсений Артём Артур Борис Вадим Валентин
Валерий Василий Виктор Виталий Владимир Владислав Всеволод Вячеслав Геннадий Георгий Глеб
Григорий Давид Даниил Денис Дмитрий Евгений Егор Захар Иван Игорь Илья Кирилл Константин
Лев Леонид Максим Матвей Михаил Никита Николай Олег Павел Пётр Роман Руслан Святослав
Семён Сергей Станислав Степан Тимофей Тимур Фёдор Филипп Эдуард Юрий Ярослав
"""

_FEMALE = """
Александра Алина Алиса Алла Анастасия Анжела Анна Антонина Валентина Валерия Варвара Вера
Вероника Виктория Галина Дарья Диана Евгения Екатерина Елена Елизавета Зинаида Инна Ирина
Карина Кира Клавдия Ксения Лариса Лидия Любовь Людмила Маргарита Марина Мария Милана
Надежда Наталья Наталия Нина Оксана Ольга Полина Раиса Регина Светлана София Софья Тамара
Татьяна Ульяна Юлия Яна
"""

_ENDINGS = frozenset(
    ["", "а", "я", "у", "ю", "ы", "и", "е", "ь", "й", "ой", "ей", "ом", "ем", "ём", "ою", "ею",
     "ью", "ия", "ии", "ию", "ие", "ием", "ий"]
)


def _norm(word: str) -> str:
    return word.lower().replace("ё", "е")


def _stem(name: str) -> str:
    stem = _norm(name)
    return stem[:-1] if stem[-1] in "аяйьеи" else stem


_STEMS = frozenset(_stem(name) for name in (_MALE + _FEMALE).split())
_PATRONYMIC = re.compile(r"[А-ЯЁ][а-яё]*(?:ович|евич|ьич|овн|евн|ичн)[а-яё]{0,3}")
_SURNAME_STRONG = re.compile(
    r"[А-ЯЁ][а-яё]*?(?:"
    r"(?:ов|ев|ёв|ин|ын)(?:а|у|ым|ом|ем|е|ы|ых|ыми)?"
    r"|(?:ова|ева|ёва|ина|ына)(?:ой|у|ы|е)?"
    r"|ск(?:ий|ого|ому|им|ом|ая|ой|ую)"
    r"|цк(?:ий|ого|ому|им|ом|ая|ой|ую)"
    r"|енко"
    r"|(?:ук|юк|чук|ян|дзе)(?:а|у|ом|е)?"
    r")"
)
_SURNAME_WEAK = re.compile(r"[А-ЯЁ][а-яё]*(?:ой|ий|ая|ый)")

NAME, PATRONYMIC, SURNAME_STRONG, SURNAME_WEAK = "name", "patronymic", "surname", "surname_weak"


def _is_first_name(word: str) -> bool:
    normalized = _norm(word)
    return any(
        normalized.startswith(stem) and normalized[len(stem) :] in _ENDINGS
        for stem in _STEMS
        if normalized[:1] == stem[:1]
    )


def classify(word: str) -> str | None:
    """Определить, на что похоже слово: отчество, фамилия, имя или ничего из этого."""
    parts = [part for part in word.split("-") if part]
    kinds = []
    for part in parts:
        if _PATRONYMIC.fullmatch(part):
            kinds.append(PATRONYMIC)
        elif _SURNAME_STRONG.fullmatch(part):
            kinds.append(SURNAME_STRONG)
        elif _is_first_name(part):
            kinds.append(NAME)
        elif _SURNAME_WEAK.fullmatch(part):
            kinds.append(SURNAME_WEAK)
    for preferred in (PATRONYMIC, SURNAME_STRONG, NAME, SURNAME_WEAK):
        if preferred in kinds:
            return preferred
    return None
