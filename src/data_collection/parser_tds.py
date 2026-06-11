# src/data_collection/parser_tds.py
import logging
from src.data_collection.pipeline import TDSPipeline

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("TDS_Parser_RND")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Вывод в консоль
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # Вывод в файл логов в директории reports
    import os
    os.makedirs("reports", exist_ok=True)
    fh = logging.FileHandler("reports/parser_run.log", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def main():
    logger = setup_logger()
    pipeline = TDSPipeline(
        raw_dir="data/01_raw",
        interim_dir="data/02_interim",
        output_path="data/03_processed/benchmarks_dataset.csv",
        logger=logger
    )
    pipeline.run_all()

if __name__ == "__main__":
    main()