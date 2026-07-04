# -*- coding: utf-8 -*-
"""SQLite 数据库模块 — 持久化存储生成记录、图片处理记录、统计数据。"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")


def get_connection() -> sqlite3.Connection:
    """获取数据库连接（每次调用创建新连接，线程安全）。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """初始化数据库表结构。"""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                style_name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                keywords TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS image_processing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                processed_name TEXT NOT NULL,
                target_width INTEGER DEFAULT 1080,
                target_height INTEGER DEFAULT 1080,
                watermark_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                style_name TEXT NOT NULL,
                method TEXT DEFAULT 'ai',
                status TEXT DEFAULT 'ok',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


# ============================================================
# 生成记录
# ============================================================


def save_generation_rows(rows: List[Dict[str, str]]) -> int:
    """批量保存生成记录到数据库。"""
    with get_connection() as conn:
        for row in rows:
            conn.execute(
                "INSERT INTO generations (product_name, style_name, prompt, keywords) VALUES (?, ?, ?, ?)",
                (row["产品名称"], row["风格"], row["Prompt"], row["关键词标签"]),
            )
        conn.commit()
        return len(rows)


def save_generation_log(product: str, style: str, method: str = "ai", status: str = "ok") -> None:
    """保存逐条生成日志。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO generation_logs (product_name, style_name, method, status) VALUES (?, ?, ?, ?)",
            (product, style, method, status),
        )
        conn.commit()


def save_image_processing(original: str, processed: str, width: int, height: int, watermark: str) -> None:
    """保存图片处理记录。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO image_processing (original_name, processed_name, target_width, target_height, watermark_text) VALUES (?, ?, ?, ?, ?)",
            (original, processed, width, height, watermark),
        )
        conn.commit()


# ============================================================
# 统计查询
# ============================================================


def get_total_prompts() -> int:
    """获取总生成数。"""
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]


def get_total_images() -> int:
    """获取总处理图片数。"""
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM image_processing").fetchone()[0]


def get_run_count() -> int:
    """获取运行次数（按批次分组）。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT DATE(created_at)) FROM generation_logs"
        ).fetchone()
        return max(row[0] or 0, 1)  # 至少 1


def get_style_counts() -> Dict[str, int]:
    """获取各风格生成数量。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT style_name, COUNT(*) as cnt FROM generations GROUP BY style_name ORDER BY style_name"
        ).fetchall()
        return {r["style_name"]: r["cnt"] for r in rows}


def get_product_counts() -> Dict[str, int]:
    """获取各产品生成数量。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_name, COUNT(*) as cnt FROM generations GROUP BY product_name ORDER BY cnt DESC"
        ).fetchall()
        return {r["product_name"]: r["cnt"] for r in rows}


def get_daily_trend(days: int = 30) -> Dict[str, int]:
    """获取最近 N 天的每日生成趋势。"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM generations
            WHERE created_at >= DATE('now', ?)
            GROUP BY day
            ORDER BY day
            """,
            (f"-{days} days",),
        ).fetchall()
        return {r["day"]: r["cnt"] for r in rows}


def get_all_stats() -> dict:
    """获取全部统计数据，供看板使用。"""
    return {
        "total_prompts": get_total_prompts(),
        "total_images": get_total_images(),
        "run_count": max(get_run_count(), 1),
        "style_counts": get_style_counts(),
        "product_counts": get_product_counts(),
        "daily_trend": get_daily_trend(),
    }
