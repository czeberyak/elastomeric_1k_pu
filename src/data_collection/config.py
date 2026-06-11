# src/config.py
import re

# Физические ограничения для валидации полиуретановых эластомеров (герметиков)
VALIDATION_LIMITS = {
    "shore_a": {"min": 5, "max": 100},
    "elongation": {"min": 50, "max": 2500},
    "skin_time": {"min": 5, "max": 600}
}

# Регулярные выражения для поиска параметров
REGEX_PATTERNS = {
    "shore_a": re.compile(
        r'(?i)\b(?:твердость(?:\s+по)?\s*(?:а\s+)?шору(?:\s*а)?|шор[а-яёa-z]{0,3}|shore\s*a(?:\s*hardness)?)\b\s*[^0-9\n]*?\s*(\d+(?:\s*(?:[±\+\-\/~\.]+|до)\s*\d+)?)\s*[aAаА]?(?!\s*%)'
    ),
    "elongation": re.compile(
        r'(?i)(?:удлинение|разрыве|elongation)(?!.*modul)(?!.*модуль).*?\%?\s*(\d{2,4}(?:\s*(?:[\-\~]|до)\s*\d{2,4})?)\s*\%?'
    ),
    "skin_time": re.compile(
        r'(?i)(?:пленк|пленкообразования|skin\s*time|tack\s*free|плотного\s+слоя|отлипа|отлипания).*?(\d+(?:\s*(?:[\-\~]|до)\s*\d+)?)\s*(мин|min|час\w*|hour\w*|ч\b|h\b)?'
    )
}

# Шаблоны очистки от климатического и метрологического шума
CLEANING_PATTERNS = {
    # Добавлен [- \s/]? перед числом для захвата IT-20, ISO-868, ГОСТ-263
    "standards": re.compile(r'(?i)\b(?:iso|din|astm|гост|en|gost|class|it)\s*[-\s/]?\s*(?:iso)?\s*\d+(?:[-\s/]\d+)?\b'),
    "seconds": re.compile(r'(?i)\b\d+\s*(?:сек|sec|секунд\w*)\b'),
    "temperatures": re.compile(r'(?i)[+-]?\d+(?:\.\d+)?\s*(?:°c|⁰c|°|⁰|ºc|º)\b'),
    "humidity": re.compile(r'(?i)\d+\s*%\s*(?:отн\.?\s*(?:вл\.?|влажн\.?)|r\.?h\.?|r\.?l\.?v\.?)\b'),
    "cure_days": re.compile(r'(?i)\b(?:через|после)?\s*\d+\s*(?:суток|дня|дней|days|dagen|дн\.?|сутки)\b')
}