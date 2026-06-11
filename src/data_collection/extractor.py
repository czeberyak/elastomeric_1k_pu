# src/data_collection/extractor.py
import logging
import pdfplumber
from pathlib import Path
from typing import List
from pdf2image import convert_from_path

logger = logging.getLogger("TDS_Parser_RND")

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
            # Вместо падения скрипта, логируем ошибку и возвращаем пустую строку
            logger.warning(f"⚠️ Пропуск {self.pdf_path.name}: файл поврежден, зашифрован или не является PDF. ({type(e).__name__})")
            return ""
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
            pass  # Таблиц в файле может не быть или файл битый
        return tables
    
    def extract_page_images(self, max_pages: int = 3) -> List:
        """
        Рендерит первые max_pages страниц PDF в объекты PIL.Image.
        Идеально для передачи в Gemini Vision API.
        """
        images = []
        try:
            # dpi=150 - оптимальный баланс между качеством распозна текста и скоростью/размером
            images = convert_from_path(self.pdf_path, dpi=150, first_page=1, last_page=max_pages)
            logger.info(f"Успешно отрендерено {len(images)} страниц из {self.pdf_path.name}")
        except Exception as e:
            logger.warning(f"Не удалось отрендерить страницы {self.pdf_path.name} для Vision API: {e}")
        return images