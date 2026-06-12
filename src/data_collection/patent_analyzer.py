# src/data_collection/patent_analyzer.py
import os
import re
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Patent_Analyzer_RND")

class PatentAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.openrouter_enabled = bool(self.api_key)
        if not self.openrouter_enabled:
            logger.warning("OPENROUTER_API_KEY не найден. Скрипт скачает тексты патентов, но авто-анализ через LLM будет недоступен.")

    def fetch_patent_data(self, patent_id: str) -> dict:
        """Программный парсинг сырого текста патента из Google Patents."""
        url = f"https://patents.google.com/patent/{patent_id}/en"
        logger.info(f"Запрос данных патента: {url}")
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Не удалось скачать патент {patent_id}: {e}")
            return {}

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем метаданные
        title_node = soup.find('meta', {'name': 'DC.title'})
        title = title_node['content'] if title_node else "Unknown Title"
        
        assignee_node = soup.find('meta', {'name': 'DC.contributor', 'scheme': 'assignee'})
        assignee = assignee_node['content'] if assignee_node else "Unknown Assignee"

        # Извлекаем формулу (Claims) и технологическое описание (Description)
        claims_section = soup.find('section', {'itemprop': 'claims'})
        claims_text = claims_section.get_text(separator=' ') if claims_section else ""

        desc_section = soup.find('section', {'itemprop': 'description'})
        desc_text = desc_section.get_text(separator=' ') if desc_section else ""

        # Усекаем текст для предотвращения переполнения контекстного окна (оставляем первые 10000 символов)
        combined_context = f"CLAIMS:\n{claims_text[:4000]}\n\nDESCRIPTION:\n{desc_text[:6000]}"
        
        return {
            "Patent_Number": patent_id,
            "Assignee": assignee,
            "Invention_Title": title,
            "Raw_Text": combined_context
        }

    def analyze_with_llm(self, patent_data: dict) -> dict:
        """Интеллектуальный анализ формулы и технологии через OpenRouter API."""
        base_result = {
            "Patent_Number": patent_data.get("Patent_Number"),
            "Assignee": patent_data.get("Assignee"),
            "Invention_Title": patent_data.get("Invention_Title"),
            "IPC_Classes": "Unknown",
            "Key_Technical_Claims": "Ошибка анализа",
            "Infringement_Risk_Level": "Medium",
            "FTO_Workaround_Strategy": "Требуется ручной анализ"
        }

        if not self.openrouter_enabled or not patent_data:
            base_result["Key_Technical_Claims"] = "LLM анализ недоступен (нет API ключа)"
            return base_result

        prompt = f"""
        Ты — патентный поверенный и Senior R&D химик в области полиуретанов.
        Проанализируй Claims и Description патента {patent_data['Patent_Number']} ("{patent_data['Invention_Title']}" от {patent_data['Assignee']}).

        Твоя задача — извлечь конкретные технологические параметры:
        1. Какие аминовые ядра заблокированы для латентных систем (например, IPDA, HMD, Jeffamine)?
        2. Какое эквивалентное соотношение латентного отвердителя к NCO группам используется?
        3. Какие температуры синтеза форполимера, вакуум дегидратации наполнителей и стабилизаторы (например, PTSI) указаны?

        На основе этого сформируй FTO-стратегию обхода (как нам синтезировать наш герметик с Shore A 20-25 и Elongation >600% без нарушения формулы этого патента).

        Верни ответ СТРОГО в формате валидного JSON без markdown-разметки и пояснений:
        {{
            "Patent_Number": "{patent_data['Patent_Number']}",
            "Assignee": "{patent_data['Assignee']}",
            "IPC_Classes": "C08G 18/12, C09K 3/10",
            "Key_Technical_Claims": "Краткое изложение формулы изобретения и параметров форполимера/алдимина",
            "Infringement_Risk_Level": "High/Medium/Low",
            "FTO_Workaround_Strategy": "Конкретные шаги по обходу патента (какой амин взять, какие соотношения поменять)"
        }}

        Текст патента:
        {patent_data['Raw_Text']}
        """

        url = "https://openrouter.ai/api/v1/chat/completions"
        # Используем те же рабочие модели, что и в parser.py
        models_to_try = [
            "openrouter/free",  
            "meta-llama/llama-3.1-8b-instruct:free"
        ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://elastomeric-pu.local",
            "X-Title": "Elastomeric PU Patent Analyzer"
        }

        for model in models_to_try:
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2048  # Увеличили для развернутого FTO-анализа
            }

            for attempt in range(2):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=45)
                    
                    if response.status_code == 429:
                        wait_time = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"⏳ OpenRouter Rate Limit (429). Ожидание {wait_time} сек...")
                        time.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    result_json = response.json()
                    content = result_json['choices'][0]['message']['content'].strip()
                    
                    # Очистка от markdown
                    if content.startswith("```"):
                        content = re.sub(r"^```(?:json)?\n|```$", "", content, flags=re.MULTILINE).strip()
                    
                    # Парсим JSON ответ
                    parsed_data = json.loads(content)
                    logger.info(f"✅ LLM успешно проанализировал патент {patent_data['Patent_Number']}")
                    return parsed_data
                    
                except json.JSONDecodeError:
                    logger.error(f"Невалидный JSON от {model}. Ответ: {content[:200] if 'content' in locals() else 'N/A'}")
                    break
                except requests.exceptions.HTTPError as e:
                    logger.error(f"HTTP Error {model}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Сбой {model}: {e}")
                    break
        
        # Если все модели не сработали, возвращаем базовый результат
        logger.warning(f"Не удалось проанализировать патент {patent_data['Patent_Number']} через LLM")
        return base_result

    def process_patents_list(self, patent_ids: list):
        records = []
        for pid in patent_ids:
            raw_data = self.fetch_patent_data(pid)
            if raw_data:
                analyzed = self.analyze_with_llm(raw_data)
                records.append(analyzed)
        
        # Сохраняем результаты в Excel-таблицу
        if records:
            df = pd.DataFrame(records)
            output_path = Path("reports/patent_landscape_analyzed.xlsx")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name="FTO_RND_Analysis", index=False)
                logger.info(f"Аналитический патентный отчет успешно сгенерирован: {output_path.resolve()}")
            except Exception as e:
                logger.error(f"Не удалось сохранить отчет: {e}")
        else:
            logger.warning("Нет данных для сохранения в Excel")


if __name__ == "__main__":
    # Запускаем анализ по ключевым патентам-конкурентам
    analyzer = PatentAnalyzer()
    analyzer.process_patents_list([
        "EP4229032B1",  # Sika: Циклоалифатические алдимины
        "US11952493B2",  # Sika: Смеси алдиминов и оксазолидинов
        "US10654964B2"   # Bostik: Влажностно-отверждаемые низкомодульные ПУ
    ])