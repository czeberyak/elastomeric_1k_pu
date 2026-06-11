# src/data_collection/parser.py
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from src.data_collection.config import REGEX_PATTERNS

class MetricsParser:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.gemini_enabled = False
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                self.gemini_enabled = True
                self.logger.info("Gemini API (новый SDK google-genai) успешно активирован.")
            except ImportError:
                self.logger.warning("Пакет 'google-genai' не найден. Установите: pip install google-genai")
        else:
            self.logger.info("GEMINI_API_KEY отсутствует. LLM Fallback отключен.")

    def parse_range_values(self, match_str: str):
        if not match_str:
            return None, None, None
        match_str = re.sub(r'\s*([±\+\-\/~\.]+)\s*', r'\1', match_str.strip())
        tolerance_match = re.search(r'(\d+(?:\.\d+)?)(?:±|(?:\+/\-))\s*(\d+(?:\.\d+)?)', match_str)
        if tolerance_match:
            center = float(tolerance_match.group(1))
            tolerance = float(tolerance_match.group(2))
            return center - tolerance, center + tolerance, center

        numbers = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', match_str)]
        if len(numbers) == 1:
            return numbers[0], numbers[0], numbers[0]
        elif len(numbers) >= 2:
            min_v = min(numbers[:2])
            max_v = max(numbers[:2])
            return min_v, max_v, (min_v + max_v) / 2.0
        return None, None, None

    def parse_from_lines(self, lines: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Шаг 1: Построчный точный Regex-поиск."""
        shore_match, elong_match, skin_match = None, None, None
        for line in lines:
            if not shore_match:
                m = REGEX_PATTERNS["shore_a"].search(line)
                if m:
                    test_val = self.parse_range_values(m.group(1))[2]
                    if test_val and 5 <= test_val <= 100:
                        shore_match = m
            if not elong_match:
                m = REGEX_PATTERNS["elongation"].search(line)
                if m: elong_match = m
            if not skin_match:
                m = REGEX_PATTERNS["skin_time"].search(line)
                if m: skin_match = m

        if shore_match:
            metrics["Shore_A_min"], metrics["Shore_A_max"], metrics["Shore_A_mean"] = self.parse_range_values(shore_match.group(1))
        if elong_match:
            metrics["Elongation_min"], metrics["Elongation_max"], metrics["Elongation_mean"] = self.parse_range_values(elong_match.group(1))
        if skin_match:
            metrics["Skin_Time_min"], metrics["Skin_Time_max"], metrics["Skin_Time_mean"] = self.parse_range_values(skin_match.group(1))
        return metrics

    def parse_from_sliding_window(self, lines: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Шаг 2: Сканирование скользящим окном для незаполненных полей."""
        window_size = 3
        combined = [" ".join(lines[i : i + window_size]) for i in range(len(lines))]
        
        for line in combined:
            if metrics["Shore_A_mean"] is None:
                m = REGEX_PATTERNS["shore_a"].search(line)
                if m:
                    test_val = self.parse_range_values(m.group(1))[2]
                    if test_val and 5 <= test_val <= 100:
                        metrics["Shore_A_min"], metrics["Shore_A_max"], metrics["Shore_A_mean"] = self.parse_range_values(m.group(1))
            if metrics["Elongation_mean"] is None:
                m = REGEX_PATTERNS["elongation"].search(line)
                if m:
                    metrics["Elongation_min"], metrics["Elongation_max"], metrics["Elongation_mean"] = self.parse_range_values(m.group(1))
            if metrics["Skin_Time_mean"] is None:
                m = REGEX_PATTERNS["skin_time"].search(line)
                if m:
                    metrics["Skin_Time_min"], metrics["Skin_Time_max"], metrics["Skin_Time_mean"] = self.parse_range_values(m.group(1))
        return metrics

    def parse_from_tables(self, tables: List[List[List[str]]], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Шаг 3: Прямой поиск показателей в изолированных таблицах."""
        if not tables:
            return metrics

        keywords = {
            "Shore_A": ["твердость", "шор", "shore"],
            "Elongation": ["удлинение", "elongation", "rek"],
            "Skin_Time": ["пленк", "skin", "tack", "плотного слоя", "отлипа"]
        }

        for table in tables:
            for row in table:
                if not row or len(row) < 2:
                    continue
                key_cell = str(row[0]).lower()
                for metric, kw_list in keywords.items():
                    if metrics[f"{metric}_mean"] is None and any(kw in key_cell for kw in kw_list):
                        for val_cell in row[1:]:
                            if not val_cell:
                                continue
                            from src.data_collection.cleaner import TextCleaner
                            cleaned_val = TextCleaner.clean_line(val_cell)
                            min_v, max_v, mean_v = self.parse_range_values(cleaned_val)
                            if mean_v is not None:
                                metrics[f"{metric}_min"] = min_v
                                metrics[f"{metric}_max"] = max_v
                                metrics[f"{metric}_mean"] = mean_v
                                self.logger.info(f"Найдено в таблице: {metric} -> {cleaned_val}")
                                break
        return metrics

    def query_gemini_vision_fallback(self, images: List, file_name: str) -> dict:
        """
        Шаг 4: LLM Vision Fallback через Gemini API (новый SDK google-genai).
        Принимает список PIL.Image объектов и извлекает метрики.
        """
        if not self.gemini_enabled or not images:
            return {}

        prompt = """
        Ты — эксперт-химик по полимерам и эластомерам. Твоя задача: извлечь технические характеристики полиуретанового герметика с изображения технической спецификации (TDS).

        Найди и извлеки ТОЛЬКО следующие 3 параметра:
        1. "Shore_A": Твердость по Шору А (число от 5 до 100). Ищи: "Shore A", "Твердость по Шору А".
        2. "Elongation": Относительное удлинение при разрыве в % (число от 100 до 1500). Ищи: "Elongation at break", "Удлинение при разрыве". НЕ путай с "Modulus" (модуль упругости)!
        3. "Skin_Time": Время образования поверхностной пленки. Если указано в часах (h, hours), умножь на 60, чтобы получить минуты. Ищи: "Skin time", "Tack free time", "Время образования пленки".

        Правила:
        - Если параметр не найден на изображении, верни для него null.
        - Если указан диапазон (например, 30-40), верни min, max и mean (среднее).
        - Если указано одно число, верни его как min, max и mean.
        
        Верни ответ СТРОГО в формате JSON, без markdown-оберток (```json), без пояснений:
        {
            "Shore_A": {"min": 20, "max": 20, "mean": 20.0},
            "Elongation": {"min": 600, "max": 600, "mean": 600.0},
            "Skin_Time": {"min": 60, "max": 60, "mean": 60.0}
        }
        """

        try:
            # Новый синтаксис google-genai: передаем модель, содержимое (промпт + картинки)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt] + images
            )
            
            # Очистка ответа от возможных markdown-оберток
            clean_str = response.text.strip()
            if clean_str.startswith("```"):
                clean_str = re.sub(r"^```(?:json)?\n|```$", "", clean_str, flags=re.MULTILINE).strip()
            
            parsed_data = json.loads(clean_str)
            self.logger.info(f"✅ Gemini Vision успешно извлек данные для {file_name}")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Gemini вернул невалидный JSON для {file_name}. Ответ: {response.text[:200]}")
            return {}
        except Exception as e:
            self.logger.error(f"Сбой Gemini Vision API для {file_name}: {e}")
            return {}