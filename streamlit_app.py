# streamlit_app.py
import sys
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
from scipy.optimize import minimize

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
        color: #2c3e50; /* Принудительно делаем текст темно-синим/серым */
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

st.warning(
    "**In silico демонстрация.** База бенчмарков собрана из открытых TDS, а отклики DOE и "
    "RSM-модель построены на **синтетических** данных: реальных лабораторных замесов в проекте "
    "пока нет. Это демонстрация методологии (парсинг TDS, DoE, RSM, оптимизация), а не готовая "
    "рецептура. Требуется калибровка и лабораторная верификация.",
    icon="⚠️",
)

# Определение путей к артефактам
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data/01_raw"
PROCESSED_CSV = BASE_DIR / "data/03_processed/benchmarks_dataset.csv"
PATENT_XLSX = BASE_DIR / "reports/patent_landscape_analyzed.xlsx"
DOE_CSV = BASE_DIR / "reports/doe_results_synthetic.csv"
FORMULATION_JSON = BASE_DIR / "reports/optimal_formulation.json"

FTO_DISCLAIMER = (
    "Патентный анализ носит информационный характер: это инженерная карта публичного "
    "патентного поиска и предварительные гипотезы по обходу, подготовленные автоматически. "
    "Это не юридическое заключение о свободе деятельности (FTO). "
    "Перед промышленным применением требуется заключение патентного поверенного."
)

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
    _pdf_count = len(list(RAW_DIR.glob("*.pdf"))) if RAW_DIR.exists() else 0
    if PROCESSED_CSV.exists():
        _stats = pd.read_csv(PROCESSED_CSV)
        _params = {"Shore A": "Shore_A_mean", "Elongation": "Elongation_mean", "Skin Time": "Skin_Time_mean"}
        st.markdown(f"- Записей в базе: {len(_stats)}")
        if _pdf_count:
            st.markdown(f"- Исходных PDF в data/01_raw: {_pdf_count}")
        if len(_stats) and all(col in _stats.columns for col in _params.values()):
            _full = int(_stats[list(_params.values())].notna().all(axis=1).sum())
            st.markdown(f"- Полных профилей (все 3 параметра): {_full}")
            st.markdown("- Заполнение: " + ", ".join(
                f"{name} {_stats[col].notna().mean() * 100:.0f}%" for name, col in _params.items()
            ))
    else:
        st.markdown("- База данных пуста")
    st.markdown("- Физическая валидация: Активна")
    
    st.markdown("---")
    st.caption("ИП Чеберяк Д.Н. R&D © 2026")

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
                    # Создаем копию текущего окружения (где pandas уже есть)
                    my_env = os.environ.copy()
                    
                    # Принудительно ставим путь к Python от Streamlit на первое место для оболочки
                    my_env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + my_env.get("PATH", "")
                    
                    # Явно указываем корень проекта, чтобы избежать ошибок импорта внутренних модулей (src...)
                    my_env["PYTHONPATH"] = str(BASE_DIR)
                    
                    # Вызываем процесс, передавая ему наше модифицированное окружение
                    result = subprocess.run(
                        ["make", "data"], 
                        capture_output=True, 
                        text=True, 
                        cwd=str(BASE_DIR),
                        env=my_env
                    )
                    
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
    st.error("⚠️ **" + FTO_DISCLAIMER + "**", icon="⚖️")
    
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
                    st.markdown(f"Предварительная оценка риска: <span class='badge {badge_class}'>{risk_level}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Ключевые формулы патента:**\n\n{row['Key_Technical_Claims']}")
                st.markdown("##### 🛡️ Гипотеза обхода (FTO Workaround, требует проверки патентным поверенным):")
                st.info(row['FTO_Workaround_Strategy'])

        st.divider()
        st.warning(FTO_DISCLAIMER, icon="⚖️")
    else:
        st.warning("Патентный ландшафт отсутствует. Запустите 'make patents' для авто-анализа патентов.")

# --- ВКЛАДКА 4: ОПТИМАЛЬНАЯ РЕЦЕПТУРА ---
# ЗАМЕНИТЕ ВЕСЬ БЛОК "with tab4:" В streamlit_app.py НА ЭТОТ КОД
# Добавьте в начало файла: from scipy.optimize import minimize

with tab4:
    st.markdown("### 🏆 Оптимальная рецептура низкомодульного герметика")
    st.markdown("Нелинейная многокритериальная SLSQP-оптимизация по поверхности отклика (RSM).")

    # ── Секция 1: Интерактивный оптимизатор ──────────────────────────────────
    st.markdown("#### ⚙️ ML-Оптимизатор рецептуры")
    st.markdown("""
    Задайте целевые свойства и запустите оптимизацию. 
    Модель RSM (поверхность отклика) рассчитает оптимальное соотношение компонентов.
    """)

    col_sl1, col_sl2, col_sl3 = st.columns(3)
    with col_sl1:
        target_shore = st.slider(
            "🎯 Целевой Shore A",
            min_value=15, max_value=40, value=22,
            help="Твёрдость по Шору А. ТЗ: 20–25"
        )
        w_shore = st.slider("Вес критерия Shore A", 0.1, 1.0, 0.4, 0.1)

    with col_sl2:
        target_elong = st.slider(
            "🎯 Целевое удлинение, %",
            min_value=300, max_value=1000, value=700,
            help="Относительное удлинение при разрыве. ТЗ: >600%"
        )
        w_elong = st.slider("Вес критерия Elongation", 0.1, 1.0, 0.4, 0.1)

    with col_sl3:
        target_skin = st.slider(
            "🎯 Целевое Skin Time, мин",
            min_value=20, max_value=120, value=55,
            help="Время образования плёнки. ТЗ: 40–70 мин"
        )
        w_skin = st.slider("Вес критерия Skin Time", 0.1, 1.0, 0.2, 0.1)

    if st.button("🚀 Запустить оптимизацию", type="primary"):
        with st.spinner("⏳ SLSQP-оптимизация по поверхности отклика..."):

            # ── RSM-модели (квадратичные апроксимации из DOE-эксперимента) ──
            # x[0] = %Prepolymer (45–65%), x[1] = %Plasticizer (10–25%), x[2] = %Filler (15–30%)
            def rsm_shore(x):
                return 8.5 + 0.18*x[0] - 0.35*x[1] + 0.12*x[2] + 0.001*x[0]**2

            def rsm_elongation(x):
                return 1200 - 8.5*x[0] + 12.0*x[1] - 6.0*x[2] - 0.05*x[0]**2

            def rsm_skin_time(x):
                return 120 - 1.2*x[0] + 0.8*x[1] - 0.3*x[2]

            # ── Функция потерь (минимизируем отклонение от целевых значений) ──
            def objective(x):
                shore_loss  = w_shore * ((rsm_shore(x)     - target_shore) / target_shore) ** 2
                elong_loss  = w_elong * ((rsm_elongation(x) - target_elong) / target_elong) ** 2
                skin_loss   = w_skin  * ((rsm_skin_time(x)  - target_skin)  / target_skin)  ** 2
                return shore_loss + elong_loss + skin_loss

            # ── Ограничения и границы ──
            constraints = [
                {"type": "eq", "fun": lambda x: x[0] + x[1] + x[2] - 85},  # сумма трёх = 85% (остаток: латент+CaO+стаб)
                {"type": "ineq", "fun": lambda x: x[0] - 45},   # Prepolymer >= 45%
                {"type": "ineq", "fun": lambda x: 65 - x[0]},   # Prepolymer <= 65%
                {"type": "ineq", "fun": lambda x: x[1] - 10},   # Plasticizer >= 10%
                {"type": "ineq", "fun": lambda x: 25 - x[1]},   # Plasticizer <= 25%
                {"type": "ineq", "fun": lambda x: x[2] - 15},   # Filler >= 15%
                {"type": "ineq", "fun": lambda x: 30 - x[2]},   # Filler <= 30%
            ]
            bounds = [(45, 65), (10, 25), (15, 30)]
            x0 = [55.0, 17.0, 13.0]

            from scipy.optimize import minimize
            result = minimize(objective, x0, method="SLSQP",
                              bounds=bounds, constraints=constraints,
                              options={"ftol": 1e-9, "maxiter": 500})

        if result.success:
            pre, plas, fill = result.x
            # Оставшиеся компоненты (фиксированные минорные добавки)
            aldimine  = 5.0
            cao       = 2.5
            salicylic = 0.5
            ptsi      = 1.5
            # Итого: pre + plas + fill + aldimine + cao + salicylic + ptsi = 100%
            # Нормируем под 100%
            total = pre + plas + fill + aldimine + cao + salicylic + ptsi
            scale = 100.0 / total

            pre_n   = round(pre * scale, 1)
            plas_n  = round(plas * scale, 1)
            fill_n  = round(fill * scale, 1)
            ald_n   = round(aldimine * scale, 1)
            cao_n   = round(cao * scale, 1)
            sal_n   = round(salicylic * scale, 1)
            ptsi_n  = round(ptsi * scale, 1)

            # Прогнозируемые свойства
            pred_shore = rsm_shore([pre_n, plas_n, fill_n])
            pred_elong = rsm_elongation([pre_n, plas_n, fill_n])
            pred_skin  = rsm_skin_time([pre_n, plas_n, fill_n])

            # Навески на 500 г замеса
            batch = 500.0
            st.success("✅ Оптимизация завершена!")

            col_res1, col_res2 = st.columns(2)

            with col_res1:
                st.markdown("#### ⚖️ Рецептурный бланк навесок (замес 500 г):")
                df_result = pd.DataFrame([
                    {"Компонент": "ПУ-Преполимер (MDI-основа)",    "%, масс.": pre_n,   "Навеска, г": round(pre_n/100*batch, 1),   "Роль": "Полимерная матрица"},
                    {"Компонент": "Пластификатор DINCH",            "%, масс.": plas_n,  "Навеска, г": round(plas_n/100*batch, 1),  "Роль": "Эластичность шва"},
                    {"Компонент": "Наполнитель CaCO₃",              "%, масс.": fill_n,  "Навеска, г": round(fill_n/100*batch, 1),  "Роль": "Тиксотропия и прочность"},
                    {"Компонент": "Латентный алдимин (D-230/2-EH)", "%, масс.": ald_n,   "Навеска, г": round(ald_n/100*batch, 1),   "Роль": "Латентный отвердитель"},
                    {"Компонент": "Оксид кальция CaO",              "%, масс.": cao_n,   "Навеска, г": round(cao_n/100*batch, 1),   "Роль": "Осушитель"},
                    {"Компонент": "Салициловая кислота",             "%, масс.": sal_n,   "Навеска, г": round(sal_n/100*batch, 1),   "Роль": "Ускоритель гидролиза"},
                    {"Компонент": "PTSI",                            "%, масс.": ptsi_n,  "Навеска, г": round(ptsi_n/100*batch, 1),  "Роль": "Термостабилизатор"},
                ])
                st.dataframe(df_result, hide_index=True, use_container_width=True)
                total_g = df_result["Навеска, г"].sum()
                st.success(f"**Итоговая масса замеса:** {total_g:.1f} г")

                # Сохраняем JSON для последующих запусков
                opt_output = {
                    "Optimizer": "SLSQP",
                    "Targets": {"Shore_A": target_shore, "Elongation": target_elong, "Skin_Time": target_skin},
                    "Weights":  {"Shore_A": w_shore, "Elongation": w_elong, "Skin_Time": w_skin},
                    "Predicted_Responses": {
                        "Shore_A": round(pred_shore, 1),
                        "Elongation_pct": round(pred_elong, 0),
                        "Skin_Time_min": round(pred_skin, 0)
                    },
                    "Weighing_Sheet_500g": {
                        "Prepolymer_g":    round(pre_n/100*batch, 1),
                        "Plasticizer_DINCH_g": round(plas_n/100*batch, 1),
                        "Filler_CaCO3_g":  round(fill_n/100*batch, 1),
                        "Aldimine_g":      round(ald_n/100*batch, 1),
                        "CaO_g":           round(cao_n/100*batch, 1),
                        "Salicylic_Acid_g":round(sal_n/100*batch, 1),
                        "PTSI_g":          round(ptsi_n/100*batch, 1),
                    }
                }
                # Пишем JSON чтобы вкладка показывала результат при следующей загрузке
                FORMULATION_JSON.parent.mkdir(parents=True, exist_ok=True)
                with open(FORMULATION_JSON, "w", encoding="utf-8") as fj:
                    import json as _json
                    _json.dump(opt_output, fj, ensure_ascii=False, indent=2)

            with col_res2:
                st.markdown("#### 🎯 Прогнозируемый физико-механический профиль:")

                def _color(val, lo, hi):
                    return "#155724" if lo <= val <= hi else "#856404" if val < lo*1.2 else "#721c24"

                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">ТВЕРДОСТЬ ПО ШОРУ А</div>
                    <div class="metric-value" style="color:{_color(pred_shore,20,25)};">{pred_shore:.1f}</div>
                    <div style="font-size:0.85rem;">ТЗ: 20–25 | Цель: {target_shore}</div>
                </div>
                <div class="metric-card" style="border-left-color:#28a745;">
                    <div class="metric-title">УДЛИНЕНИЕ ПРИ РАЗРЫВЕ</div>
                    <div class="metric-value" style="color:{_color(pred_elong,600,1000)};">{pred_elong:.0f}%</div>
                    <div style="font-size:0.85rem;">ТЗ: &gt;600% | Цель: {target_elong}%</div>
                </div>
                <div class="metric-card" style="border-left-color:#ffc107;">
                    <div class="metric-title">ВРЕМЯ ОБРАЗОВАНИЯ ПЛЁНКИ</div>
                    <div class="metric-value" style="color:{_color(pred_skin,40,70)};">{pred_skin:.0f} мин</div>
                    <div style="font-size:0.85rem;">ТЗ: 40–70 мин | Цель: {target_skin} мин</div>
                </div>
                """, unsafe_allow_html=True)

                # Радарная диаграмма соответствия ТЗ
                import matplotlib.pyplot as plt
                import numpy as np
                fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
                categories = ["Shore A\n(норм.)", "Elongation\n(норм.)", "Skin Time\n(норм.)"]
                # Нормируем: 1.0 = попадание в середину ТЗ
                vals = [
                    min(pred_shore / 22.5, 1.0),
                    min(pred_elong / 700, 1.0),
                    min(pred_skin / 55, 1.0),
                ]
                vals += vals[:1]
                angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
                angles += angles[:1]
                ax.plot(angles, vals, "o-", linewidth=2, color="#2980b9")
                ax.fill(angles, vals, alpha=0.25, color="#2980b9")
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(categories, fontsize=9)
                ax.set_ylim(0, 1.2)
                ax.set_title("Соответствие ТЗ", pad=15)
                st.pyplot(fig)

        else:
            st.error(f"❌ Оптимизатор не сошёлся: {result.message}")
            st.info("Попробуйте изменить целевые значения или веса критериев.")

    # ── Секция 2: Загрузка сохранённого результата (если JSON существует) ────
    st.markdown("---")
    if FORMULATION_JSON.exists():
        with open(FORMULATION_JSON, "r", encoding="utf-8") as f:
            opt_data = json.load(f)

        st.markdown("#### 📂 Последний сохранённый результат оптимизации:")
        col_sv1, col_sv2 = st.columns(2)

        with col_sv1:
            st.markdown("**Рецептурный бланк навесок (замес 500 г):**")
            ws = opt_data.get("Weighing_Sheet_500g", {})
            df_saved = pd.DataFrame([
                {"Компонент": "ПУ-Преполимер (MDI-основа)",    "Навеска, г": ws.get("Prepolymer_g", "—")},
                {"Компонент": "Пластификатор DINCH",            "Навеска, г": ws.get("Plasticizer_DINCH_g", "—")},
                {"Компонент": "Наполнитель CaCO₃",              "Навеска, г": ws.get("Filler_CaCO3_g", "—")},
                {"Компонент": "Латентный алдимин (D-230/2-EH)", "Навеска, г": ws.get("Aldimine_g", "—")},
                {"Компонент": "Оксид кальция CaO",              "Навеска, г": ws.get("CaO_g", "—")},
                {"Компонент": "Салициловая кислота",             "Навеска, г": ws.get("Salicylic_Acid_g", "—")},
                {"Компонент": "PTSI",                            "Навеска, г": ws.get("PTSI_g", "—")},
            ])
            st.dataframe(df_saved, hide_index=True, use_container_width=True)

        with col_sv2:
            preds = opt_data.get("Predicted_Responses", {})
            st.markdown("**Прогнозируемый профиль свойств:**")
            st.metric("Shore A", preds.get("Shore_A", "—"))
            st.metric("Удлинение", f"{preds.get('Elongation_pct', '—')}%")
            st.metric("Skin Time", f"{preds.get('Skin_Time_min', '—')} мин")

# Футер
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; font-size: 0.85rem;">
    <strong>AI Materials Informatics для тяжелой промышленности</strong> | Автоматизация R&D процессов ПУ<br>
    
</div>
""", unsafe_allow_html=True)