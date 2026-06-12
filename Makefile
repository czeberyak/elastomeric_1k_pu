.PHONY: help data patents audit dashboard all clean

help: ## Показать справку по доступным командам
	@echo "🚀 Доступные команды R&D пайплайна:"
	@echo "  make data      - Парсинг TDS конкурентов и очистка датасета"
	@echo "  make patents   - Поиск и FTO-анализ патентов (LLM)"
	@echo "  make audit     - Аудит качества и заполненности датасета"
	@echo "  make dashboard - Генерация аналитического дашборда"
	@echo "  make all       - Полный цикл обновления всех данных"
	@echo "  make clean     - Очистка временных файлов и кэша"

data: ## Сбор и очистка данных TDS
	@echo "📊 Запуск парсера TDS..."
	python3 -m src.data_collection.parser_tds
	@echo "🧹 Очистка датасета..."
	python3 -m src.data_collection.cleanup

patents: ## Поиск и анализ патентов
	@echo "⚖️ Запуск патентного поиска и FTO-анализа..."
	python3 -m src.data_collection.patent_analyzer

audit: ## Аудит качества данных
	@echo "🔍 Запуск аудита датасета..."
	python3 -m src.analysis.data_audit

dashboard: ## Генерация дашборда
	@echo "📈 Генерация дашборда..."
	python3 -m src.data_collection.patent_dashboard

all: data patents audit ## Запустить полный цикл обновления данных
	@echo "✅ Полный цикл R&D-разведки завершен! Откройте notebooks/01_data_exploration.ipynb"

clean: ## Очистка кэша и временных файлов
	@echo "🧹 Очистка __pycache__ и временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Очистка завершена."