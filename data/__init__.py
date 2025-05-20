# data/__init__.py
from .loader import load_db, DB_PATH, SCORES_TABLE_NAME, STATS_TABLE_NAME

__all__ = ["load_db", "DB_PATH", "SCORES_TABLE_NAME", "STATS_TABLE_NAME"] 