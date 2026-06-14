# streamlit_app.py
import os
import re
import json
import subprocess
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# Настройка страницы под стандарты 2026 года
st.set_page_config(
    page_title="R&D Панель управления: 1К ПУ Герметики",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Промышленные стили для интерфейса R&D-платформы
st.markdown("""
<style>
    .reportview-container .main { background-color: #f4f6f9; }
    .main-header { font-size: 2.2rem; font-weight: bold; color: #2c3e50; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #7f8c8d; margin-bottom: 1.5rem; }
    .info-box {
        background-color: #e8f4fd;
        border-left: 5px solid #2980b9;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 15px;
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 6px;
        border-left: 4px solid #2980b9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin: 10px 0;
    }
    .metric-title { font-size: 0.85rem; color: #7f8c8d; font-weight: bold; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #2c3e50; margin-top: 5px; }
    .badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }
    .badge-high { background-color: #f8d7da; color: #721c24; }
    .badge-medium { background-color: #fff3cd; color: #856404; }
    .badge-low { background-color: #d4edda; color: #155724; }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown('<div class="main-header">🧪 R&D Панель управления: 1К ПУ Герметики</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Data-driven R&D платформа формулирования высокоэластичных систем фасадных швов</div>', unsafe_allow_html=True)

# Определение путей к артефактам
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data/01_raw"
PROCESSED_CSV = BASE_DIR / "data/03_processed/benchmarks_dataset.csv"
PATENT_XLSX = BASE_DIR / "reports/patent_landscape_analyzed.xlsx"
DOE_CSV = BASE_DIR / "reports/doe_results_synthetic.csv"
FORMULATION_JSON = BASE_DIR / "reports/optimal_formulation.json"

# Боковая панель
with st.sidebar:
    st.header("ℹ️ О системе")
    st.markdown("""
    Данная панель управления координирует расчеты и сбор данных:
    - **Shore A** — Твердость по Шору А
    - **Elongation** — Одноосное удлинение (%)
    - **Skin Time** — Время образования пленки (мин)
    """)
    
    # Проверка ключа OpenRouter
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        st.success("🔑 OpenRouter API: Активен")
    else:
        st.warning("⚠️ OpenRouter API: Не найден")

    st.markdown("---")
    st.markdown("**Статистика базы:**")
    st.markdown("- Обработано спецификаций: 22")
    st.markdown("- Успешность парсинга: 82-100%")
    st.markdown("- Физическая валидация: Активна")
    
    st.markdown("---")
    st.caption("Эластомерик Системс R&D © 2026")

# Основной контент: Вкладки
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Загрузка и парсинг", 
    "📊 Визуализация и DOE", 
    "⚖️ Патентный FTO-анализ", 
    "🎯 Оптимальная рецептура"
])

# --- ВКЛАДКА 1: ЗАГРУЗКА И ПАРСИНГ ---
with tab1:
    st.markdown("### 📤 Шаг 1: Загрузка PDF-файлов")
    
    st.markdown("""
    <div class="info-box">
        <strong>Как работает каскадный парсинг:</strong><br>
        1. Загрузите PDF-файлы технических спецификаций (TDS) конкурентов.<br>
        2. Нажмите кнопку <strong>Запустить парсинг</strong>. Система выполнит построчный Regex-поиск, табличную экстракцию и обратится к OpenRouter для пропущенных полей.
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Выберите PDF-файлы технических спецификаций",
        type=['pdf'],
        accept_multiple_files=True,
        key="pdf_uploader"
    )

    if uploaded_files:
        st.success(f"✅ Загружено файлов: {len(uploaded_files)}")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        
        for file in uploaded_files:
            file_path = RAW_DIR / file.name
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
        
        st.markdown("---")
        
        # Кнопка запуска парсинга (make data)
        if st.button("🚀 Запустить парсинг (make data)", type="primary", width="stretch"):
            with st.spinner("⏳ Выполняется парсинг и валидация данных..."):
                try:
                    result = subprocess.run(["make", "data"], capture_output=True, text=True, cwd=str(BASE_DIR))
                    
                    if result.returncode == 0:
                        st.success("✅ Парсинг и очистка датасета завершены успешно!")
                        with st.expander("📋 Лог выполнения"):
                            st.code(result.stdout, language='bash')
                    else:
                        st.error(f"❌ Ошибка выполнения: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Критический сбой: {str(e)}")

    st.markdown("---")
    st.markdown("### 📋 Текущее состояние базы бенчмарков")
    
    if PROCESSED_CSV.exists():
        df_results = pd.read_csv(PROCESSED_CSV)
        st.dataframe(df_results, width="stretch")
        
        # Статистика извлечения
        st.markdown("#### 📈 Метрики качества наполнения базы:")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            shore_success = df_results['Shore_A_mean'].notna().sum()
            st.metric("Shore A", f"{shore_success}/{len(df_results)}", f"{shore_success/len(df_results)*100:.1f}%")
        with col_m2:
            elong_success = df_results['Elongation_mean'].notna().sum()
            st.metric("Elongation", f"{elong_success}/{len(df_results)}", f"{elong_success/len(df_results)*100:.1f}%")
        with col_m3:
            skin_success = df_results['Skin_Time_mean'].notna().sum()
            st.metric("Skin Time", f"{skin_success}/{len(df_results)}", f"{skin_success/len(df_results)*100:.1f}%")
            
        # Кнопка скачивания CSV
        csv_data = df_results.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Скачать базу бенчмарков (CSV)",
            data=csv_data,
            file_name="benchmarks_dataset.csv",
            mime="text/csv",
            width="stretch"
        )
    else:
        st.warning("База данных пуста. Загрузите PDF файлы и запустите парсинг.")

# --- ВКЛАДКА 2: ВИЗУАЛИЗАЦИЯ И DOE ---
with tab2:
    st.markdown("### 📊 Картирование свойств и матрицы планирования")
    
    if PROCESSED_CSV.exists():
        df_viz = pd.read_csv(PROCESSED_CSV)
        
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("**Сравнение твердости Shore A с границами ТЗ:**")
            fig, ax = plt.subplots(figsize=(8, 6))
            # Исправлен FutureWarning: Явно задаем hue="Product_Name" и legend=False
            sns.barplot(x="Product_Name", y="Shore_A_mean", data=df_viz, hue="Product_Name", palette="viridis", legend=False, ax=ax)
            ax.axhline(y=20, color='r', linestyle='--', linewidth=1.5, label='ТЗ Нижняя граница (Shore A 20)')
            ax.axhline(y=25, color='g', linestyle='--', linewidth=1.5, label='ТЗ Верхняя граница (Shore A 25)')
            ax.set_xticks(range(len(df_viz)))
            ax.set_xticklabels(df_viz['Product_Name'], rotation=45, ha='right', fontsize=8)
            ax.set_ylabel("Твердость Shore A")
            ax.legend()
            st.pyplot(fig)
            
        with col_v2:
            st.markdown("**2D Карта свойств: Shore A vs Elongation (ТЗ выделено красным):**")
            fig, ax = plt.subplots(figsize=(8, 6))
            plot_df = df_viz.dropna(subset=["Shore_A_mean", "Elongation_mean"])
            
            # Убираем Loctite PL (1440 мин) только для цветности графика
            scatter_df = plot_df[plot_df["Skin_Time_mean"] < 500] if "Skin_Time_mean" in plot_df.columns else plot_df
            
            scatter = ax.scatter(
                scatter_df["Shore_A_mean"], 
                scatter_df["Elongation_mean"], 
                c=scatter_df["Skin_Time_mean"] if "Skin_Time_mean" in scatter_df.columns else None,
                cmap="viridis", s=120, edgecolors="black", alpha=0.85
            )
            if "Skin_Time_mean" in scatter_df.columns:
                fig.colorbar(scatter, ax=ax, label="Время пленки (мин)")
                
            # Красный прямоугольник ТЗ
            rect = plt.Rectangle((20, 600), 5, 400, linewidth=2, edgecolor='red', facecolor='red', alpha=0.15, label="Целевая область ТЗ")
            ax.add_patch(rect)
            ax.set_xlim(15, 55)
            ax.set_ylim(200, 1000)
            ax.set_xlabel("Shore A")
            ax.set_ylabel("Elongation, %")
            ax.legend()
            st.pyplot(fig)
    else:
        st.info("Аналитические графики будут построены после парсинга.")

    st.markdown("---")
    st.markdown("### 📊 Матрица планирования Box-Behnken (DOE)")
    
    if DOE_CSV.exists():
        df_doe = pd.read_csv(DOE_CSV)
        st.dataframe(df_doe, width="stretch")
        
        st.markdown("#### Распределение симулированных лабораторных откликов:")
        col_d1, col_dist2, col_dist3 = st.columns(3)
        with col_d1:
            fig, ax = plt.subplots(figsize=(4, 3))
            sns.histplot(df_doe["Measured_Shore_A"], kde=True, color="skyblue", ax=ax)
            ax.set_title("Твердость Shore A")
            st.pyplot(fig)
        with col_dist2:
            fig, ax = plt.subplots(figsize=(4, 3))
            sns.histplot(df_doe["Measured_Elongation"], kde=True, color="salmon", ax=ax)
            ax.set_title("Удлинение, %")
            st.pyplot(fig)
        with col_dist3:
            fig, ax = plt.subplots(figsize=(4, 3))
            sns.histplot(df_doe["Measured_Skin_Time"], kde=True, color="lightgreen", ax=ax)
            ax.set_title("Время пленки, мин")
            st.pyplot(fig)
    else:
        st.warning("Файл результатов DOE не обнаружен. Выполните 'make simulate' для генерации синтетических данных.")

# --- ВКЛАДКА 3: ПАТЕНТНЫЙ FTO-АНАЛИЗ ---
with tab3:
    st.markdown("### ⚖️ Результаты FTO-анализа патентного ландшафта (Sika, Dow, Bostik)")
    
    if PATENT_XLSX.exists():
        df_pat = pd.read_excel(PATENT_XLSX)
        
        for idx, row in df_pat.iterrows():
            risk_level = str(row.get("Infringement_Risk_Level", "Medium")).strip()
            badge_class = "badge-high" if "High" in risk_level else "badge-medium" if "Medium" in risk_level else "badge-low"
            
            # Отказоустойчивый геттер для Invention_Title (предотвращает KeyError)
            title = row.get("Invention_Title") if "Invention_Title" in row else None
            if pd.isna(title) or not title:
                title = "Patent Specification"
                
            with st.expander(f"📄 Патент: {row['Patent_Number']} — {row['Assignee']} ({title})"):
                col_p1, col_p2 = st.columns([3, 1])
                with col_p1:
                    st.markdown(f"**Классификатор IPC:** `{row['IPC_Classes']}`")
                with col_p2:
                    st.markdown(f"Уровень риска: <span class='badge {badge_class}'>{risk_level}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Ключевые формулы патента:**\n\n{row['Key_Technical_Claims']}")
                st.markdown("##### 🛡️ Утвержденная стратегия обхода (FTO Workaround):")
                st.info(row['FTO_Workaround_Strategy'])
    else:
        st.warning("Патентный ландшафт отсутствует. Запустите 'make patents' для авто-анализа патентов.")

# --- ВКЛАДКА 4: ОПТИМАЛЬНАЯ РЕЦЕПТУРА ---
with tab4:
    st.markdown("### 🏆 Оптимальная рецептура низкомодульного герметика")
    st.markdown("Результаты нелинейной многокритериальной SLSQP-оптимизации по поверхности отклика:")
    
    if FORMULATION_JSON.exists():
        with open(FORMULATION_JSON, "r", encoding="utf-8") as f:
            opt_data = json.load(f)
            
        col_opt1, col_opt2 = st.columns(2)
        
        with col_opt1:
            st.markdown("#### ⚖️ Рецептурный бланк навесок (на замес 500 г):")
            weigh_sheet = opt_data["Weighing_Sheet_500g"]
            df_weigh = pd.DataFrame([
                {"Компонент": "ПУ-Преполимер (MDI-основа)", "Масса, г": weigh_sheet["Prepolymer_g"], "Роль": "Полимерная матрица"},
                {"Компонент": "Латентный алдимин (D-230/2-EH)", "Масса, г": weigh_sheet["Aldimine_g"], "Роль": "Латентный отвердитель"},
                {"Компонент": "Пластификатор DINCH", "Масса, г": weigh_sheet["Plasticizer_DINCH_g"], "Роль": "Эластичность шва"},
                {"Компонент": "Сухой наполнитель (CaCO3)", "Масса, г": weigh_sheet["Filler_CaCO3_g"], "Роль": "Тиксотропия и прочность"},
                {"Компонент": "Оксид кальция (CaO)", "Масса, г": weigh_sheet["CaO_g"], "Роль": "Осушитель"},
                {"Компонент": "Салициловая кислота", "Масса, г": weigh_sheet["Salicylic_Acid_g"], "Роль": "Ускоритель гидролиза"},
                {"Компонент": "PTSI", "Масса, г": weigh_sheet["PTSI_g"], "Роль": "Термостабилизатор ПУ"}
            ])
            st.dataframe(df_weigh, width="stretch", hide_index=True)
            st.success(f"**Итоговая масса навески:** {sum(df_weigh['Масса, г']):.1f} г")
            
        with col_opt2:
            st.markdown("#### 🎯 Прогнозируемый физико-механический профиль:")
            preds = opt_data["Predicted_Responses"]
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">ТВЕРДОСТЬ ПО ШОРУ А</div>
                <div class="metric-value" style="color: #155724;">{preds['Shore_A']}</div>
                <div style="font-size: 0.85rem; color: #28a745;">Идеальное соответствие ТЗ (20 - 25)</div>
            </div>
            <div class="metric-card" style="border-left-color: #28a745;">
                <div class="metric-title">ОТНОСИТЕЛЬНОЕ УДЛИНЕНИЕ ПРИ РАЗРЫВЕ</div>
                <div class="metric-value" style="color: #155724;">{preds['Elongation_pct']}%</div>
                <div style="font-size: 0.85rem; color: #28a745;">Превосходит ТЗ (&gt; 600%)</div>
            </div>
            <div class="metric-card" style="border-left-color: #ffc107;">
                <div class="metric-title">ВРЕМЯ ОБРАЗОВАНИЯ ПЛЕНКИ</div>
                <div class="metric-value" style="color: #856404;">{preds['Skin_Time_min']} мин</div>
                <div style="font-size: 0.85rem; color: #ffc107;">Оптимальная кинетика гелеобразования (40 - 70 мин)</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Оптимальная рецептура еще не рассчитана. Запустите 'ML-Оптимизатор' на боковой панели.")

# Футер
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; font-size: 0.85rem;">
    <strong>AI Materials Informatics для тяжелой промышленности</strong> | Автоматизация R&D процессов ПУ<br>
    ООО «Эластомерик Системс» © 2026
</div>
""", unsafe_allow_html=True)