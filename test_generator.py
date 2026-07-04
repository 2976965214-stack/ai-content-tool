# -*- coding: utf-8 -*-
"""Prompt 生成器单元测试。"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_generator import (
    read_product_names,
    generate_single_prompt_template,
    generate_keywords,
    generate_prompts,
    write_excel,
    write_csv,
    DEFAULT_STYLES,
)


def test_generate_single_prompt_template():
    """测试模板生成 Prompt 格式正确。"""
    prompt = generate_single_prompt_template("无线耳机", "minimalist style")
    assert "无线耳机" in prompt
    assert "minimalist style" in prompt
    assert "Product photography" in prompt
    assert prompt.startswith("Product photography")


def test_generate_keywords():
    """测试关键词标签生成。"""
    tags = generate_keywords("无线耳机", "北欧简约")
    assert "无线耳机" in tags
    assert "北欧简约" in tags
    assert "product_photography" in tags


def test_generate_prompts_count():
    """测试生成数量正确。"""
    products = ["手机", "手表"]
    styles = DEFAULT_STYLES[:2]  # 只取前 2 个风格
    rows = generate_prompts(products, styles, use_ai=False)
    assert len(rows) == 4  # 2 产品 x 2 风格
    for row in rows:
        assert "产品名称" in row
        assert "风格" in row
        assert "Prompt" in row
        assert "关键词标签" in row


def test_generate_prompts_content():
    """测试生成内容非空。"""
    rows = generate_prompts(["耳机"], DEFAULT_STYLES[:1], use_ai=False)
    assert len(rows) == 1
    row = rows[0]
    assert row["产品名称"] == "耳机"
    assert row["风格"] == DEFAULT_STYLES[0][0]
    assert len(row["Prompt"]) > 20
    assert len(row["关键词标签"]) > 5


def test_generate_prompts_empty_products():
    """测试空产品列表返回空。"""
    rows = generate_prompts([], DEFAULT_STYLES[:1], use_ai=False)
    assert len(rows) == 0


def test_generate_prompts_empty_styles():
    """测试空风格列表返回空。"""
    rows = generate_prompts(["耳机"], [], use_ai=False)
    assert len(rows) == 0


def test_write_excel(tmp_path):
    """测试 Excel 写入。"""
    rows = [{"产品名称": "测试", "风格": "北欧", "Prompt": "test", "关键词标签": "test"}]
    path = tmp_path / "test.xlsx"
    write_excel(rows, str(path))
    assert os.path.getsize(path) > 0


def test_write_csv(tmp_path):
    """测试 CSV 写入。"""
    rows = [{"产品名称": "测试", "风格": "北欧", "Prompt": "test", "关键词标签": "test"}]
    path = tmp_path / "test.csv"
    write_csv(rows, str(path))
    assert os.path.getsize(path) > 0


def test_read_product_names(tmp_path):
    """测试读取 Excel 产品名称。"""
    import pandas as pd
    df = pd.DataFrame({"产品名称": ["A", "B", "C"]})
    path = tmp_path / "test.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    products = read_product_names(str(path))
    assert products == ["A", "B", "C"]


def test_read_product_names_missing_column(tmp_path):
    """测试缺少列时报错。"""
    import pandas as pd
    df = pd.DataFrame({"其他列": ["A"]})
    path = tmp_path / "bad.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    with pytest.raises(ValueError, match="找不到列"):
        read_product_names(str(path))


def test_read_product_names_empty(tmp_path):
    """测试空数据时报错。"""
    import pandas as pd
    df = pd.DataFrame({"产品名称": []})
    path = tmp_path / "empty.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    with pytest.raises(ValueError, match="没有有效数据"):
        read_product_names(str(path))