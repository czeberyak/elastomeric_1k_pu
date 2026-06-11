# src/data_collection/pipeline.py
import logging
from pathlib import Path
import pandas as pd
from src.data_collection.extractor import PDFExtractor
from src.data_collection.cleaner import TextCleaner
from src.data_collection.parser import MetricsParser
from src.data_collection.validator import DataValidator

class TDSPipeline:
    def __init__(self, raw_dir: str, interim_dir: str, output_path: str, logger: logging.Logger):
        self.raw_dir = Path(raw_dir)
        self.interim_dir = Path(interim_dir)
        self.output_path = Path(output_path)
        self.logger = logger
        self.parser = MetricsParser(logger)

    def run_single(self, pdf_path: Path) -> dict:
        self.logger.info(f"Обработка файла: {pdf_path.name}")
        
        # 1. Извлечение
        extractor = PDFExtractor(pdf_path)
        raw_text = extractor.extract_text()
        tables = extractor.extract_tables()

        # Сохраняем промежуточный плоский текст
        self.interim_dir.mkdir(parents=True, exist_ok=True)
        with open(self.interim_dir / pdf_path.name.replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
            f.write(raw_text)

        # 2. Очистка
        cleaned_lines = TextCleaner.process_text(raw_text)

        # Структура записи
        metrics = {
            "Source_File": pdf_path.name, "Product_Name": "Unknown",
            "Shore_A_min": None, "Shore_A_max": None, "Shore_A_mean": None,
            "Elongation_min": None, "Elongation_max": None, "Elongation_mean": None,
            "Skin_Time_min": None, "Skin_Time_max": None, "Skin_Time_mean": None
        }

        # Вытаскиваем имя продукта
        for line in cleaned_lines[:8]:
            line_strip = line.strip()
            if any(keyword in line_strip.lower() for keyword in ["герметик", "клей", "sealant", "adhesive", "sika", "bostik"]):
                if len(line_strip) > 5 and not line_strip.startswith(('Техническое', 'Technical', 'Product Data', 'Паспорт')):
                    metrics["Product_Name"] = line_strip
                    break
        if metrics["Product_Name"] == "Unknown":
            metrics["Product_Name"] = pdf_path.stem

        # 3. Каскадный парсинг
        metrics = self.parser.parse_from_lines(cleaned_lines, metrics)
        
        if any(metrics[k] is None for k in ["Shore_A_mean", "Elongation_mean", "Skin_Time_mean"]):
            metrics = self.parser.parse_from_sliding_window(cleaned_lines, metrics)

        if any(metrics[k] is None for k in ["Shore_A_mean", "Elongation_mean", "Skin_Time_mean"]):
            metrics = self.parser.parse_from_tables(tables, metrics)

        # LLM Fallback
        missing = []
        if metrics["Shore_A_mean"] is None: missing.append("Shore_A")
        if metrics["Elongation_mean"] is None: missing.append("Elongation")
        if metrics["Skin_Time_mean"] is None: missing.append("Skin_Time")

        if missing and self.parser.gemini_enabled:
            self.logger.info(f"Запуск Gemini Fallback для {pdf_path.name} по полям: {missing}")
            gemini_data = self.parser.query_gemini_fallback(raw_text, missing)
            for key in missing:
                if gemini_data.get(key) is not None:
                    metrics[f"{key}_min"] = gemini_data[key].get("min")
                    metrics[f"{key}_max"] = gemini_data[key].get("max")
                    metrics[f"{key}_mean"] = gemini_data[key].get("mean")
                    self.logger.info(f"Gemini Fallback успешно восстановил {key}: {metrics[f'{key}_mean']}")

        # Корректировка Skin Time при обнаружении часов
        sk_mean = metrics["Skin_Time_mean"]
        if sk_mean is not None and any(unit in raw_text.lower() for unit in ["час", "hour", " ч ", " h "]) and not any(unit in raw_text.lower() for unit in ["мин", "min"]):
            metrics["Skin_Time_min"] = metrics["Skin_Time_min"] * 60 if metrics["Skin_Time_min"] else None
            metrics["Skin_Time_max"] = metrics["Skin_Time_max"] * 60 if metrics["Skin_Time_max"] else None
            metrics["Skin_Time_mean"] = metrics["Skin_Time_mean"] * 60 if metrics["Skin_Time_mean"] else None

        # 4. Валидация
        metrics = DataValidator.validate_metrics(metrics, pdf_path.name, self.logger)
        # В методе run_single(), после DataValidator.validate_metrics()
        self.logger.info(
            f"✅ {pdf_path.name} | {metrics['Product_Name']} | "
            f"Shore: {metrics['Shore_A_mean']} | "
            f"Elong: {metrics['Elongation_mean']}% | "
            f"Skin: {metrics['Skin_Time_mean']} мин"
        )
        return metrics        

    def run_all(self):
        pdf_files = list(self.raw_dir.glob("*.pdf"))
        if not pdf_files:
            self.logger.warning("Нет файлов в data/01_raw.")
            return

        records = [self.run_single(f) for f in pdf_files]
        df = pd.DataFrame(records)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.output_path, index=False, encoding="utf-8")
        self.logger.info("Пайплайны успешно завершены. Датасет собран.")