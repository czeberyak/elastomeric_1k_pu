# src/data_collection/cleanup.py
import pandas as pd
from pathlib import Path

def clean_and_finalize_dataset():
    dataset_path = Path("data/03_processed/benchmarks_dataset.csv")
    if not dataset_path.exists():
        print("Исходный датасет не найден.")
        return

    df = pd.read_csv(dataset_path)

    # 1. Жесткая фильтрация нерелевантных систем и пустых строк
    # Исключаем 2К системы (Shore A >= 60) и строки, где все три физических параметра равны NaN
    df = df[df["Shore_A_mean"] < 60]
    df = df.dropna(subset=["Shore_A_mean", "Elongation_mean", "Skin_Time_mean"], how="all")

    # 2. Нормализация наименований продуктов (убираем расширения файлов и мусорные префиксы)
    def normalize_name(row):
        name = str(row["Product_Name"])
        if name == "Unknown" or name.lower().endswith(".pdf") or "_" in name:
            # Восстанавливаем имя из названия файла
            base = Path(row["Source_File"]).stem
            base = base.replace("_", " ").replace("-", " ").title()
            return base
        return name

    df["Product_Name"] = df.apply(normalize_name, axis=1)

    # 3. Ручные корректировки аномалий, выявленных при валидации
    # Исправляем Loctite PL (24 часа переводим в 1440 минут)
    df.loc[df["Source_File"] == "loctite_pl.pdf", ["Skin_Time_min", "Skin_Time_max", "Skin_Time_mean"]] = 1440.0

    # 4. Сохранение очищенного датасета
    df.to_csv(dataset_path, index=False, encoding="utf-8")
    print(f"Датасет успешно очищен. Сохранено {len(df)} валидных профилей.")

if __name__ == "__main__":
    clean_and_finalize_dataset()