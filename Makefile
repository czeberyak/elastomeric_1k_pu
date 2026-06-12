.PHONY: help data patents dashboard all clean

help: ## Показать справку
	@echo "🚀 Доступные команды пайплайна:"
	@echo "  make data      - Парсинг TDS конкурентов и очистка датасета"
	@echo "  make patents   - Поиск и парсинг патентов"
	@echo "  make dashboard - Генерация аналитического дашборда"
	@echo "  make all       - Полный цикл обновления всех данных"
	@echo "  make clean     - Очистка временных файлов"

data: ## Сбор и очистка данных TDS
	@echo "📊 Запуск парсера TDS..."
	python3 -m src.data_collection.parser_tds
	@echo "🧹 Очистка датасета..."
	python3 -m src.data_collection.cleanup

patents: ## Поиск патентов
	@echo "📜 Запуск поиска патентов..."
	python3 -m src.data_collection.patent_search

dashboard: ## Генерация дашборда
	@echo "📈 Генерация дашборда..."
	python3 -m src.data_collection.patent_dashboard

all: data patents dashboard ## Запустить ВСЁ подряд
	@echo "✅ Полный цикл обновления данных завершен!"

clean: ## Очистка кэша и временных файлов
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete