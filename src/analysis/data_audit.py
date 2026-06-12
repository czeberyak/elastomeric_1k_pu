import pandas as pd
import matplotlib.pyplot as plt

def run_dataset_audit(data: pd.DataFrame):
    """Проводит аудит заполненности датасета и выводит визуальный отчет (для Jupyter)."""
    print("="*65)
    print("📊 АУДИТ ДАТАСЕТА TDS ПУ-ГЕРМЕТИКОВ")
    print("="*65)
    
    total = len(data)
    print(f"Всего профилей продуктов в сырой выборке: {total}\n")
    
    metrics = ['Shore_A_mean', 'Elongation_mean', 'Skin_Time_mean']
    metric_names = ['Твердость (Shore A)', 'Удлинение (Elongation)', 'Время пленки (Skin Time)']
    
    print("📈 Заполненность метрик (успешность парсинга LLM/Regex):")
    fill_rates = []
    for m, name in zip(metrics, metric_names):
        count = data[m].notna().sum()
        pct = (count / total) * 100
        fill_rates.append(pct)
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"{name:<25} | {bar} | {count}/{total} ({pct:.1f}%)")
        
    complete = data.dropna(subset=metrics)
    print(f"\n🏆 Идеальные профили (все 3 метрики): {len(complete)} из {total}")
    
    print("\n⚠️ Продукты, требующие ручного ввода (отсутствует >= 2 метрик):")
    missing_count = data[metrics].isna().sum(axis=1)
    critical_missing = data[missing_count >= 2][['Product_Name', 'Shore_A_mean', 'Elongation_mean', 'Skin_Time_mean']]
    
    if critical_missing.empty:
        print("   ✅ Критически пустых профилей нет, отличная работа парсера!")
    else:
        for _, row in critical_missing.iterrows():
            print(f"   ❌ {row['Product_Name']}: Shore={row['Shore_A_mean']}, Elong={row['Elongation_mean']}, Skin={row['Skin_Time_mean']}")
            
    print("="*65)
    
    # Визуализация заполненности (Data Completeness)
    fig, ax = plt.subplots(figsize=(8, 2.5))
    colors = ['#2ca02c' if x == 100 else '#ff7f0e' if x > 80 else '#d62728' for x in fill_rates]
    
    ax.barh(metric_names[::-1], fill_rates[::-1], color=colors[::-1], edgecolor='black')
    ax.set_xlim(0, 108)
    ax.set_xlabel('Процент заполненности (%)')
    ax.set_title('Карта покрытия датасета метриками (Data Completeness)', fontweight='bold')
    
    for i, v in enumerate(fill_rates[::-1]):
        ax.text(v + 1, i, f"{v:.1f}%", va='center', fontweight='bold')
        
    plt.tight_layout()
    plt.show()

def run_audit(csv_path: str = "data/03_processed/benchmarks_dataset.csv"):
    """Точка входа для запуска из терминала (python -m src.analysis.data_audit)."""
    df = pd.read_csv(csv_path)
    run_dataset_audit(df)

if __name__ == "__main__":
    run_audit()