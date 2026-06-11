import os
import re
import glob
import pandas as pd
import pdfplumber

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
        print(f"Ошибка при чтении {os.path.basename(pdf_path)}: {e}")
    return full_text

def parse_tds_metrics(text, file_name):
    """
    Ищет ключевые физико-химические маркеры в тексте с помощью Regex.
    Возвращает словарь с очищенными данными.
    """
    # 1. Попытка определить коммерческое имя продукта (обычно первая строка или ключевые слова)
    product_name = file_name
    first_line = text.split('\n')[0].strip() if text else ""
    if len(first_line) > 3 and not first_line.startswith('%'):
        product_name = first_line

    # 2. Паттерны Regex (настроены на русские и английские термины)
    # Ищем Шор А (цифры от 10 до 90)
    shore_pattern = r'(?:Твердость|Шор|Shore\s+A)[\s\D]*(\d{2})'
    
    # Ищем удлинение при разрыве (значения обычно от 100% до 1200%)
    elongation_pattern = r'(?:Удлинение|разрыве|Elongation)[\s\D]*(\d{3,4})\s*%'
    
    # Ищем время образования пленки (в минутах, обычно 10-180 мин)
    skin_time_pattern = r'(?:Пленк|пленкообразования|Skin\s+time|tack\s+free)[\s\D]*(\d{2,3})\s*(?:мин|min)'

    # Экстракция данных с помощью безопасного поиска (.search)
    shore_a = re.search(shore_pattern, text, re.IGNORECASE)
    elongation = re.search(elongation_pattern, text, re.IGNORECASE)
    skin_time = re.search(skin_time_pattern, text, re.IGNORECASE)

    return {
        "Source_File": file_name,
        "Product_Predicted_Name": product_name,
        "Shore_A": int(shore_a.group(1)) if shore_a else None,
        "Elongation_Percent": int(elongation.group(1)) if elongation else None,
        "Skin_Time_Min": int(skin_time.group(1)) if skin_time else None,
    }

def main():
    # Пути в соответствии с нашей структурой проекта
    raw_data_dir = "data/01_raw"
    output_path = "data/03_processed/benchmarks_dataset.csv"
    
    pdf_files = glob.glob(os.path.join(raw_data_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"В папке {raw_data_dir} не найдено PDF-файлов для обработки.")
        return

    print(f"Найдено {len(pdf_files)} файлов для анализа...")
    parsed_records = []

    for pdf_path in pdf_files:
        file_name = os.path.basename(pdf_path)
        print(f"Обработка: {file_name} -> ", end="")
        
        # Шаг 1: Извлечение сырого текста
        raw_text = extract_text_from_pdf(pdf_path)
        
        # Опционально: можно сохранить промежуточный текст в data/02_interim
        interim_txt_path = os.path.join("data/02_interim", file_name.replace(".pdf", ".txt"))
        with open(interim_txt_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
            
        # Шаг 2: Структурирование данных
        metrics = parse_tds_metrics(raw_text, file_name)
        print(f"Успешно. Считано: Шор А={metrics['Shore_A']}, Удлинение={metrics['Elongation_Percent']}%")
        
        parsed_records.append(metrics)

    # Шаг 3: Формирование финального датасета
    df = pd.DataFrame(parsed_records)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\nСбор данных завершен. Датасет сохранен в: {output_path}")

if __name__ == "__main__":
    main()