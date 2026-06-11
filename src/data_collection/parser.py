# src/data_collection/parser.py
import os
import re
import json
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from src.data_collection.config import REGEX_PATTERNS

class MetricsParser:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.provider = None
        self.api_key = None
        
        # Приоритет: OpenRouter (стабильнее для РФ), затем Groq
        if os.environ.get("OPENROUTER_API_KEY"):
            self.provider = "openrouter"
            self.api_key = os.environ.get("OPENROUTER_API_KEY")
            self.logger.info("✅ OpenRouter API Fallback успешно активирован.")
        elif os.environ.get("GROQ_API_KEY"):
            self.provider = "groq"
            self.api_key = os.environ.get("GROQ_API_KEY")
            self.logger.info("✅ Groq API Fallback активирован (возможны лимиты).")
        else:
            self.logger.warning("OPENROUTER_API_KEY / GROQ_API_KEY не найдены. LLM Fallback отключен.")

    def parse_range_values(self, match_str: str):
        """Парсит строку с цифрами и возвращает (min_val, max_val, mean_val)."""
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
            mean_v = (min_v + max_v) / 2.0
            return min_v, max_v, mean_v
            
        return None, None, None

    def parse_from_lines(self, lines: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Этап 1: Построчный точный Regex-поиск."""
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
                if m:
                    elong_match = m
            if not skin_match:
                m = REGEX_PATTERNS["skin_time"].search(line)
                if m:
                    skin_match = m

        if shore_match:
            metrics["Shore_A_min"], metrics["Shore_A_max"], metrics["Shore_A_mean"] = self.parse_range_values(shore_match.group(1))
        if elong_match:
            metrics["Elongation_min"], metrics["Elongation_max"], metrics["Elongation_mean"] = self.parse_range_values(elong_match.group(1))
        if skin_match:
            metrics["Skin_Time_min"], metrics["Skin_Time_max"], metrics["Skin_Time_mean"] = self.parse_range_values(skin_match.group(1))
        return metrics

    def parse_from_sliding_window(self, lines: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Этап 2: Поиск скользящим окном."""
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
        """Этап 3: Прямой поиск в таблицах."""
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

    # CHANGED: Переименован метод для совместимости с pipeline.py
        # CHANGED: Переименован метод для совместимости с pipeline.py
    def query_gemini_vision_fallback(self, raw_text: str, file_name: str) -> Dict[str, Any]:
        """Этап 4: LLM Fallback через OpenRouter с актуальными бесплатными моделями."""
        if not self.provider:
            return {}

        prompt = f"""
Ты — эксперт-химик по полиуретановым герметикам. Извлеки технические характеристики из текста TDS.

Найди и верни ТОЛЬКО следующие параметры:
1. "Shore_A": Твердость по Шору А (число от 5 до 100).
2. "Elongation": Относительное удлинение при разрыве в % (число от 100 до 1500). НЕ путай с "Modulus"!
3. "Skin_Time": Время образования поверхностной пленки в МИНУТАХ. Если в часах — умножь на 60.

Правила:
- Если параметр не найден, верни null.
- Если указан диапазон (30-40), верни min, max и mean.
- Если одно число, верни его как min, max и mean.

Верни СТРОГО JSON без markdown:
{{
    "Shore_A": {{"min": 20, "max": 20, "mean": 20.0}},
    "Elongation": null,
    "Skin_Time": null
}}

Текст TDS:
---
{raw_text[:8000]}
---
"""

            # ... (начало метода и prompt остаются без изменений) ...

        if self.provider == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
            # Используем умный роутер - он автоматически выберет доступную бесплатную модель
            models_to_try = [
                "openrouter/free",  # Автоматический выбор из всех free моделей
                "meta-llama/llama-3.2-3b-instruct:free",  # Резервный вариант
            ]
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://elastomeric-pu.local",
                "X-Title": "Elastomeric PU TDS Parser",
            }
        else: # groq
            url = "https://api.groq.com/openai/v1/chat/completions"
            models_to_try = ["llama3-70b-8192"]
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

        # Цикл по моделям и попыткам (защита от 429)
        for model in models_to_try:
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1024  # Увеличили с 500 до 1024, чтобы избежать 400 Bad Request
            }

            for attempt in range(2):  # 2 попытки на каждую модель
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    
                    # Обработка Rate Limit (429)
                    if response.status_code == 429:
                        wait_time = int(response.headers.get("Retry-After", 60))
                        self.logger.warning(f"⏳ OpenRouter Rate Limit (429). Ожидание {wait_time} сек...")
                        time.sleep(wait_time)
                        continue  # Повторяем попытку
                    
                    response.raise_for_status()
                    result_json = response.json()
                    content = result_json['choices'][0]['message']['content'].strip()
                    
                    if content.startswith("```"):
                        content = re.sub(r"^```(?:json)?\n|```$", "", content, flags=re.MULTILINE).strip()
                    
                    parsed_data = json.loads(content)
                    self.logger.info(f"✅ {model} успешно извлек данные для {file_name}")
                    return parsed_data
                    
                except json.JSONDecodeError:
                    self.logger.error(f"Невалидный JSON от {model}. Ответ: {content[:200]}")
                    break  # Ломать JSON нет смысла повторять, пробуем следующую модель
                except requests.exceptions.HTTPError as e:
                    self.logger.error(f"HTTP Error {model}: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"Сбой {model}: {e}")
                    break

        return {}