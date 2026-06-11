# src/data_collection/validator.py
from typing import Dict, Any, Optional
import logging
from src.data_collection.config import VALIDATION_LIMITS

class DataValidator:
    @staticmethod
    def validate_metrics(metrics: Dict[str, Any], file_name: str, logger: logging.Logger) -> Dict[str, Any]:
        mapping = {
            "shore_a": "Shore_A",
            "elongation": "Elongation",
            "skin_time": "Skin_Time"
        }
        for metric, limit in VALIDATION_LIMITS.items():
            prefix = mapping[metric]
            val = metrics.get(f"{prefix}_mean")
            if val is not None:
                if not (limit["min"] <= val <= limit["max"]):
                    logger.warning(f"[{file_name}] {prefix} ({val}) вне физических пределов [{limit['min']} - {limit['max']}]. Сброс.")
                    metrics[f"{prefix}_min"] = None
                    metrics[f"{prefix}_max"] = None
                    metrics[f"{prefix}_mean"] = None
        return metrics