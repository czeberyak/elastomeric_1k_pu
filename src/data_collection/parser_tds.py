import os
import re
import glob
import logging
import pandas as pd
import pdfplumber

# Настройка логирования по стандарту R&D
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TDS_Parser_RND")


def extract_text_from_pdf(pdf_path):
    """Извлекает весь текст из PDF-файла по страницам."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        logger.error(f"Ошибка при чтении {os.path.basename(pdf_path)}: {e}")
    return full_text


def clean_noise(line: str) -> str:
    """
    Вырезает климатические параметры, сроки выдержки, секунды и стандарты до парсинга,
    чтобы исключить ложные мэтчи паразитных чисел.
    """
    if not line:
        return ""
    
    # 1. Срезаем стандарты и их номера (ISO, DIN, ASTM, ГОСТ, EN, IT)
    line = re.sub(r'(?i)\b(?:iso|din|astm|гост|en|gost|class|it)\s*(?:iso)?\s*\d+(?:[-\s/]\d+)?\b', '', line)
    
    # 2. Срезаем длительность в секундах (например, 3 секунды, 3 сек, 3 sec) - актуально для методик вдавливания индентора
    line = re.sub(r'(?i)\b\d+\s*(?:сек|sec|секунд\w*)\b', '', line)
    
    # 3. Срезаем температуры измерения (например, 23 °C, 23°C, +23 °C, -20 °C, 23⁰C)
    line = re.sub(r'(?i)[+-]?\d+(?:\.\d+)?\s*(?:°c|⁰c|°|⁰|ºc|º)\b', '', line)
    
    # 4. Срезаем относительную влажность воздуха (например, 50% отн. вл., 50 % R.H., 50% RH)
    line = re.sub(r'(?i)\d+\s*%\s*(?:отн\.?\s*(?:вл\.?|влажн\.?)|r\.?h\.?|r\.?l\.?v\.?)\b', '', line)
    
    # 5. Срезаем сроки выдержки образцов (например, 28 дней, 28 days, 7 дней, 14 дней)
    line = re.sub(r'(?i)\b(?:через|после)?\s*\d+\s*(?:суток|дня|дней|days|dagen|дн\.?|сутки)\b', '', line)
    
    # Убираем дублирующие пробелы
    line = re.sub(r'\s+', ' ', line).strip()
    return line


def parse_range_values(match_str: str):
    """Принимает строку с цифрами и возвращает (min_val, max_val, mean_val)."""
    if not match_str:
        return None, None, None
    
    match_str = re.sub(r'\s*([±\+\-\/~\.]+)\s*', r'\1', match_str.strip())
    
    # 1. Поиск структуры толеранса (номинал ± допуск)
    tolerance_match = re.search(r'(\d+(?:\.\d+)?)(?:±|(?:\+/\-))\s*(\d+(?:\.\d+)?)', match_str)
    if tolerance_match:
        center = float(tolerance_match.group(1))
        tolerance = float(tolerance_match.group(2))
        return center - tolerance, center + tolerance, center

    # 2. Поиск стандартных числовых диапазонов или одиночных чисел
    numbers = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', match_str)]
    
    if len(numbers) == 1:
        return numbers[0], numbers[0], numbers[0]
    elif len(numbers) >= 2:
        min_v = min(numbers[:2])
        max_v = max(numbers[:2])
        mean_v = (min_v + max_v) / 2.0
        return min_v, max_v, mean_v
        
    return None, None, None


def validate_and_sanitize(metrics: dict, file_name: str) -> dict:
    """Физико-химический контроль собранных данных эластомеров."""
    if metrics["Shore_A_mean"] is not None:
        if not (5 <= metrics["Shore_A_mean"] <= 100):
            logger.warning(f"[{file_name}] Shore A ({metrics['Shore_A_mean']}) вне диапазона 5-100. Сброс.")
            metrics["Shore_A_min"] = metrics["Shore_A_max"] = metrics["Shore_A_mean"] = None
            
    if metrics["Elongation_mean"] is not None:
        if not (100 <= metrics["Elongation_mean"] <= 2500):
            logger.warning(f"[{file_name}] Elongation ({metrics['Elongation_mean']}%) вне диапазона 100-2500. Сброс.")
            metrics["Elongation_min"] = metrics["Elongation_max"] = metrics["Elongation_mean"] = None
            
    if metrics["Skin_Time_mean"] is not None:
        if not (5 <= metrics["Skin_Time_mean"] <= 600):
            logger.warning(f"[{file_name}] Skin Time ({metrics['Skin_Time_mean']} мин) вне диапазона 5-600. Сброс.")
            metrics["Skin_Time_min"] = metrics["Skin_Time_max"] = metrics["Skin_Time_mean"] = None
            
    return metrics


def parse_tds_metrics(text, file_name):
    """Прогрессивный двухэтапный парсер показателей."""
    default_record = {
        "Source_File": file_name, "Product_Name": "Unknown",
        "Shore_A_min": None, "Shore_A_max": None, "Shore_A_mean": None,
        "Elongation_min": None, "Elongation_max": None, "Elongation_mean": None,
        "Skin_Time_min": None, "Skin_Time_max": None, "Skin_Time_mean": None
    }
    
    if not text:
        return default_record

    cleaned_text = text.replace('\xa0', ' ')
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
    raw_lines = cleaned_text.split('\n')

    # Очищаем все строки от климатического шума
    lines = [clean_noise(line) for line in raw_lines]

    # Определение имени продукта
    product_name = "Unknown"
    for line in lines[:8]:
        line_strip = line.strip()
        if any(keyword in line_strip.lower() for keyword in ["герметик", "клей", "sealant", "adhesive", "sika", "bostik"]):
            if len(line_strip) > 5 and not line_strip.startswith(('Техническое', 'Technical', 'Product Data', 'Паспорт')):
                product_name = line_strip
                break
    if product_name == "Unknown":
        product_name = os.path.splitext(file_name)[0]

    # Инициализируем регулярные выражения
    # shore_rx: разделитель заменен на [^0-9\n]*?, что позволяет поглощать любые промежуточные тексты/скобки, не переходя на новые строки
    shore_rx = re.compile(
        r'(?i)\b(?:твердость(?:\s+по)?\s*(?:а\s+)?шору(?:\s*а)?|шор[а-яёa-z]{0,3}|shore\s*a(?:\s*hardness)?)\b\s*[^0-9\n]*?\s*(\d+(?:\s*(?:[±\+\-\/~\.]+|до)\s*\d+)?)(?!\s*%)'
    )
    elong_rx = re.compile(
        r'(?i)(?:удлинение|разрыве|elongation).*?\%?\s*(\d{2,4}(?:\s*(?:[\-\~]|до)\s*\d{2,4})?)\s*\%?'
    )
    skin_rx = re.compile(
        r'(?i)(?:пленк|пленкообразования|skin\s*time|tack\s*free|плотного\s+слоя|отлипа|отлипания).*?(\d+(?:\s*(?:[\-\~]|до)\s*\d+)?)\s*(мин|min|час\w*|hour\w*|ч\b|h\b)?'
    )

    shore_match, elong_match, skin_match = None, None, None

    # === ЭТАП 1: Точный построчный поиск (High Precision) ===
    for line in lines:
        if not shore_match:
            m = shore_rx.search(line)
            if m:
                test_val = parse_range_values(m.group(1))[2]
                if test_val and 5 <= test_val <= 100:
                    shore_match = m
        if not elong_match:
            m = elong_rx.search(line)
            if m:
                elong_match = m
        if not skin_match:
            m = skin_rx.search(line)
            if m:
                skin_match = m

    # === ЭТАП 2: Фолбэк на скользящее окно (High Recall) ===
    if not shore_match or not elong_match or not skin_match:
        window_size = 3
        combined_lines = []
        for i in range(len(lines)):
            window = " ".join(lines[i : i + window_size])
            combined_lines.append(window)

        for line in combined_lines:
            if not shore_match:
                m = shore_rx.search(line)
                if m:
                    test_val = parse_range_values(m.group(1))[2]
                    if test_val and 5 <= test_val <= 100:
                        shore_match = m
            if not elong_match:
                m = elong_rx.search(line)
                if m:
                    elong_match = m
            if not skin_match:
                m = skin_rx.search(line)
                if m:
                    skin_match = m

    # Десериализация результатов
    sh_min, sh_max, sh_mean = parse_range_values(shore_match.group(1) if shore_match else None)
    el_min, el_max, el_mean = parse_range_values(elong_match.group(1) if elong_match else None)
    sk_min, sk_max, sk_mean = parse_range_values(skin_match.group(1) if skin_match else None)

    # Корректировка Skin Time при обнаружении часов
    final_skin_match = skin_match
    if final_skin_match and sk_mean is not None:
        matched_text = final_skin_match.group(0).lower()
        if any(unit in matched_text for unit in ["час", "hour", " ч", " h"]) and not any(unit in matched_text for unit in ["мин", "min"]):
            if sk_min is not None: sk_min *= 60
            if sk_max is not None: sk_max *= 60
            if sk_mean is not None: sk_mean *= 60
            logger.info(f"[{file_name}] Обнаружено время в часах. Автоконвертация в минуты: {sk_mean}")

    metrics = {
        "Source_File": file_name,
        "Product_Name": product_name,
        "Shore_A_min": sh_min, "Shore_A_max": sh_max, "Shore_A_mean": sh_mean,
        "Elongation_min": el_min, "Elongation_max": el_max, "Elongation_mean": el_mean,
        "Skin_Time_min": sk_min, "Skin_Time_max": sk_max, "Skin_Time_mean": sk_mean
    }

    metrics = validate_and_sanitize(metrics, file_name)
    return metrics


def main():
    raw_data_dir = "data/01_raw"
    output_path = "data/03_processed/benchmarks_dataset.csv"
    
    pdf_files = glob.glob(os.path.join(raw_data_dir, "*.pdf"))
    if not pdf_files:
        logger.warning("Нет файлов для обработки в data/01_raw.")
        return

    parsed_records = []
    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        raw_text = extract_text_from_pdf(pdf_path)
        
        interim_txt_path = os.path.join("data/02_interim", file_name.replace(".pdf", ".txt"))
        try:
            with open(interim_txt_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception as e:
            logger.error(f"Не удалось сохранить текст для {file_name}: {e}")
            
        metrics = parse_tds_metrics(raw_text, file_name)
        parsed_records.append(metrics)
        logger.info(f"Обработан {file_name} -> Название: {metrics['Product_Name']}, Shore_A_mean: {metrics['Shore_A_mean']}, Elongation_mean: {metrics['Elongation_mean']}, Skin_Time_mean: {metrics['Skin_Time_mean']}")

    df = pd.DataFrame(parsed_records)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Чистый ML-ready датасет сохранен в: {output_path}")


if __name__ == "__main__":
    main()