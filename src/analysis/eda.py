# src/analysis/eda.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def run_eda():
    dataset_path = Path("data/03_processed/benchmarks_dataset.csv")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    if not dataset_path.exists():
        print("Датасет не найден. Сначала запустите парсер.")
        return

    df = pd.read_csv(dataset_path)

    # 1. Расчет базовых статистик для R&D-отчета
    metrics = ["Shore_A_mean", "Elongation_mean", "Skin_Time_mean"]
    stats = df[metrics].describe()
    
    print("\n=== Статистический профиль рынка конкурентов ===")
    print(stats.to_string())
    
    # Запись статистического отчета
    stats.to_csv(reports_dir / "market_statistics.csv")

    # 2. Корреляционный анализ (Пирсон)
    corr_pearson = df[metrics].corr(method='pearson')
    print("\n=== Корреляционная матрица (Pearson) ===")
    print(corr_pearson)

    # Построение тепловой карты корреляций
    plt.figure(figsize=(6, 5))
    sns.heatmap(corr_pearson, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f")
    plt.title("Корреляция физико-механических показателей")
    plt.tight_layout()
    plt.savefig(reports_dir / "correlation_heatmap.png", dpi=300)
    plt.close()

    # 3. Распределения показателей (Boxplots и KDE)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    sns.histplot(df["Shore_A_mean"].dropna(), kde=True, ax=axes[0], color="skyblue")
    axes[0].set_title("Распределение твердости (Shore A)")
    axes[0].set_xlabel("Shore A")

    sns.histplot(df["Elongation_mean"].dropna(), kde=True, ax=axes[1], color="salmon")
    axes[1].set_title("Распределение удлинения (%)")
    axes[1].set_xlabel("Elongation, %")

    sns.histplot(df["Skin_Time_mean"].dropna(), kde=True, ax=axes[2], color="lightgreen")
    axes[2].set_title("Распределение времени пленки (мин)")
    axes[2].set_xlabel("Skin Time, min")
    
    plt.suptitle("Гистограммы распределения свойств ПУ-герметиков", fontsize=14)
    plt.tight_layout()
    plt.savefig(reports_dir / "property_distributions.png", dpi=300)
    plt.close()

    # 4. Двумерное распределение (Shore A vs Elongation) с цветовой кодировкой времени пленки
    plt.figure(figsize=(8, 6))
    
    # Исключаем Loctite PL (1440 мин) только для графика, чтобы не ломать цветовую шкалу
    plot_df = df[df["Skin_Time_mean"] < 500]
    
    scatter = plt.scatter(
        plot_df["Shore_A_mean"], 
        plot_df["Elongation_mean"], 
        c=plot_df["Skin_Time_mean"], 
        cmap="viridis", 
        s=100, 
        edgecolors="black",
        alpha=0.8
    )
    plt.colorbar(scatter, label="Время пленки (мин)")
    plt.xlabel("Твердость по Шору А")
    plt.ylabel("Относительное удлинение при разрыве (%)")
    plt.title("Карта рыночных бенчмарков: Shore A vs Elongation")
    plt.grid(True, linestyle="--", alpha=0.5)
    
    # Наносим на карту целевую область нашего ТЗ (Shore A 20-25, Elongation > 600%)
    rect = plt.Rectangle((20, 600), 5, 400, linewidth=2, edgecolor='red', facecolor='red', alpha=0.15, label="Целевое ТЗ")
    plt.gca().add_patch(rect)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(reports_dir / "target_space_mapping.png", dpi=300)
    plt.close()
    
    print(f"\nАнализ завершен. Графики и отчеты сохранены в директорию '{reports_dir}/'")

if __name__ == "__main__":
    run_eda()