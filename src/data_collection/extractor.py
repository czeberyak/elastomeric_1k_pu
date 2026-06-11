# src/data_collection/extractor.py
import pdfplumber
from pathlib import Path
from typing import List

class PDFExtractor:
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        """Постраничное извлечение плоского текста."""
        full_text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения {self.pdf_path.name}: {e}")
        return full_text

    def extract_tables(self) -> List[List[List[str]]]:
        """Извлечение табличных структур."""
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    extracted_tables = page.extract_tables()
                    for table in extracted_tables:
                        if table:
                            tables.append(table)
        except Exception:
            pass  # Таблиц в файле может не быть
        return tables