# src/data_collection/patent_search.py
import os
import pandas as pd
from pathlib import Path

def generate_patent_landscape_template():
    reports_dir = Path("reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = reports_dir / "patent_landscape.xlsx"
    
    # 1. Структура ландшафта патентов-конкурентов
    landscape_data = [
        {
            "Patent_Number": "EP4229032B1",
            "Assignee": "Sika Technology AG",
            "IPC_Classes": "C08G 18/10, C08G 18/12, C09J 175/08",
            "Invention_Title": "Cycloaliphatic aldimine mixture as latent hardeners",
            "Key_Technical_Claims": "Использование смесей циклоалифатических алдиминов на основе IPDA для снижения вязкости и исключения запаха при отверждении.",
            "Infringement_Risk_Level": "High",
            "FTO_Workaround_Strategy": "Использовать алифатические линейные алдимины или блокированные кетимины без циклоалифатического ядра, оптимизировать эквивалентное соотношение."
        },
        {
            "Patent_Number": "US11952493B2",
            "Assignee": "Sika Technology AG",
            "IPC_Classes": "C08L 75/08, C08G 18/12",
            "Invention_Title": "Moisture-curing polyurethane composition containing oxazolidine & aldimine",
            "Key_Technical_Claims": "Комбинация оксазолидинов и алдиминов в соотношении 0.3-0.8 к NCO группам для безпузырькового отверждения.",
            "Infringement_Risk_Level": "Medium",
            "FTO_Workaround_Strategy": "Исключить оксазолидины из системы. Применять строго моно-функциональные латентные отвердители (моно-алдимины) для снижения модуля упругости."
        },
        {
            "Patent_Number": "EP1155093B1",
            "Assignee": "Dow Chemical / Essex",
            "IPC_Classes": "C09K 3/10, C08G 18/12",
            "Invention_Title": "Polyurethane sealant compositions",
            "Key_Technical_Claims": "Однокомпонентные герметики на базе форполимеров с высокой прочностью на сдвиг и контролируемым временем пленки.",
            "Infringement_Risk_Level": "Medium",
            "FTO_Workaround_Strategy": "Ориентироваться на низкомодульный сегмент (Shore A 20-25) с высокой концентрацией пластификатора DINCH, исключая фталатные пластификаторы, запатентованные Dow."
        }
    ]

    # 2. Поля для заполнения в процессе поиска
    empty_template_fields = [
        "Patent_Number", "Assignee", "IPC_Classes", "Invention_Title", 
        "Key_Technical_Claims", "Infringement_Risk_Level", "FTO_Workaround_Strategy"
    ]
    
    # Создаем DataFrame
    df_existing = pd.DataFrame(landscape_data)
    
    # Добавляем 10 пустых строк для ручной фиксации находок Дмитрия
    empty_rows = pd.DataFrame([[None] * len(empty_template_fields) for _ in range(10)], columns=empty_template_fields)
    df_final = pd.concat([df_existing, empty_rows], ignore_index=True)
    
    # Сохраняем в Excel с использованием pandas/openpyxl
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_final.to_excel(writer, sheet_name="FTO_Matrix", index=False)
        print(f"Патентная FTO-матрица сгенерирована и сохранена в: {file_path}")
        print("Базовые патенты-угрозы от Sika и Dow успешно занесены в реестр.")
    except Exception as e:
        print(f"Ошибка сохранения Excel (проверьте наличие openpyxl): {e}")

if __name__ == "__main__":
    generate_patent_landscape_template()