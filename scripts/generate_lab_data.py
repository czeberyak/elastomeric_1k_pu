"""
Генератор синтетических лабораторных данных для DOE матрицы.
Имитирует реальные измерения с добавлением экспериментального шума.
"""
import pandas as pd
import numpy as np
from pathlib import Path

def generate_synthetic_results():
    # 📍 Автоматически находим корень проекта (папка scripts -> родительская папка)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    
    doe_csv = PROJECT_ROOT / "reports" / "doe_bbd_matrix.csv"
    output_csv = PROJECT_ROOT / "reports" / "doe_results_synthetic.csv"
    
    np.random.seed(42)
    
    # Загружаем DOE матрицу
    print(f"📂 Чтение матрицы DOE из: {doe_csv}")
    df = pd.read_csv(doe_csv)
    
    # Переменные
    nco = df['NCO_free_pct'].values
    plast = df['Plasticizer_wt_pct'].values / 100.0  # доли
    fill = df['Filler_wt_pct'].values / 100.0
    
    # --- ПОЛУЭМПИРИЧЕСКИЕ МОДЕЛИ (Physics-Informed) ---
    # 1. Предсказание Shore A
    base_shore = 10.0 + (18.0 * nco * (1.0 / (1.0 + 3.0 * plast))) * (1.0 + 1.2 * (fill ** 2))
    
    # 2. Предсказание Elongation %
    base_elong = (1500.0 + 1200.0 * (plast ** 1.5)) * (1.0 / (1.0 + 0.4 * nco)) * (1.0 / (1.0 + 1.5 * fill))
    
    # 3. Предсказание Skin Time, мин
    base_skin = (80.0 / nco) * (1.0 + 0.4 * fill)
    
    # --- Добавляем экспериментальный шум ---
    noise_shore = np.random.normal(0, 1.5, size=len(df))
    noise_elong = base_elong * np.random.normal(0, 0.08, size=len(df))
    noise_skin = np.random.normal(0, 5, size=len(df))
    
    # Финальные измерения
    df['Measured_Shore_A'] = np.round(base_shore + noise_shore, 1)
    df['Measured_Elongation'] = np.round(base_elong + noise_elong, 0).astype(int)
    df['Measured_Skin_Time'] = np.round(base_skin + noise_skin, 1)
    
    # Клиппинг физических границ
    df['Measured_Shore_A'] = df['Measured_Shore_A'].clip(5, 100)
    df['Measured_Elongation'] = df['Measured_Elongation'].clip(50, 2500)
    df['Measured_Skin_Time'] = df['Measured_Skin_Time'].clip(5, 600)
    
    # Сохраняем
    df.to_csv(output_csv, index=False, encoding='utf-8')
    
    print(f"✅ Синтетические данные сгенерированы и сохранены: {output_csv.name}")
    print(f"\n📊 Сводная статистика измерений:")
    print(df[['Measured_Shore_A', 'Measured_Elongation', 'Measured_Skin_Time']].describe().round(2))
    
    in_spec = df[
        (df['Measured_Shore_A'] >= 20) & (df['Measured_Shore_A'] <= 25) &
        (df['Measured_Elongation'] >= 600) &
        (df['Measured_Skin_Time'] >= 40) & (df['Measured_Skin_Time'] <= 70)
    ]
    print(f"\n🎯 Количество точек, попадающих в ТЗ: {len(in_spec)} из {len(df)}")
    
    return df

if __name__ == "__main__":
    generate_synthetic_results()