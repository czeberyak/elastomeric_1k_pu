# src/data_collection/cleaner.py
import re
from typing import List
from src.data_collection.config import CLEANING_PATTERNS

class TextCleaner:
    @staticmethod
    def clean_line(line: str) -> str:
        """Построчная зачистка шума."""
        if not line:
            return ""
        line = CLEANING_PATTERNS["standards"].sub('', line)
        line = CLEANING_PATTERNS["seconds"].sub('', line)
        line = CLEANING_PATTERNS["temperatures"].sub('', line)
        line = CLEANING_PATTERNS["humidity"].sub('', line)
        line = CLEANING_PATTERNS["cure_days"].sub('', line)
        return re.sub(r'\s+', ' ', line).strip()

    @classmethod
    def process_text(cls, raw_text: str) -> List[str]:
        """Нормализация сырого текста и разбивка на очищенные строки."""
        cleaned = raw_text.replace('\xa0', ' ')
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        return [cls.clean_line(line) for line in cleaned.split('\n')]