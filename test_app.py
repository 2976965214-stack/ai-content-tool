# -*- coding: utf-8 -*-
"""Flask 应用集成测试。"""

import os
import sys
import json
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置测试环境变量
os.environ["FLASK_ENV"] = "testing"


@pytest.fixture
def app():
    """创建测试 Flask 应用实例。"""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
    flask_app.config["PROCESSED_FOLDER"] = tempfile.mkdtemp()
    return flask_app


@pytest.fixture
def client(app):
    """创建测试客户端。"""
    return app.test_client()


def test_index_page(client):
    """测试首页渲染。"""
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"AI Content Tool" in rv.data
    assert b"批量生成" in rv.data
    assert b"图片处理" in rv.data
    assert b"数据看板" in rv.data


def test_stats_api(client):
    """测试统计接口返回正确格式。"""
    rv = client.get("/api/stats")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "total_prompts" in data
    assert "total_images" in data
    assert "style_counts" in data
    assert "product_counts" in data
    assert "daily_trend" in data


def test_upload_no_file(client):
    """测试未传文件时返回 400。"""
    rv = client.post("/api/upload")
    assert rv.status_code == 400


def test_upload_wrong_format(client):
    """测试非 xlsx 格式返回 400。"""
    rv = client.post("/api/upload", data={"file": (open(__file__, "rb"), "test.py")})
    assert rv.status_code == 400


def test_generate_no_styles(client):
    """测试未选风格时返回 400。"""
    rv = client.post(
        "/api/generate",
        data=json.dumps({"products": ["耳机"], "styles": []}),
        content_type="application/json",
    )
    assert rv.status_code == 400


def test_generate_success(client):
    """测试正常生成。"""
    rv = client.post(
        "/api/generate",
        data=json.dumps({"products": ["耳机", "手表"], "styles": ["北欧简约", "科技感"]}),
        content_type="application/json",
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["total"] == 4  # 2 产品 x 2 风格
    assert len(data["rows"]) == 4
    for row in data["rows"]:
        assert "Prompt" in row
        assert len(row["Prompt"]) > 20


def test_export_excel(client):
    """测试导出 Excel。"""
    rv = client.post(
        "/api/export",
        data=json.dumps({
            "rows": [{"产品名称": "A", "风格": "B", "Prompt": "C", "关键词标签": "D"}],
            "format": "excel",
        }),
        content_type="application/json",
    )
    assert rv.status_code == 200
    assert rv.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_export_csv(client):
    """测试导出 CSV。"""
    rv = client.post(
        "/api/export",
        data=json.dumps({
            "rows": [{"产品名称": "A", "风格": "B", "Prompt": "C", "关键词标签": "D"}],
            "format": "csv",
        }),
        content_type="application/json",
    )
    assert rv.status_code == 200
    assert rv.mimetype == "text/csv"


def test_export_empty(client):
    """测试空数据导出返回 400。"""
    rv = client.post(
        "/api/export",
        data=json.dumps({"rows": [], "format": "excel"}),
        content_type="application/json",
    )
    assert rv.status_code == 400


def test_generate_then_stats(client):
    """测试生成后统计数据更新。"""
    # 先获取当前总数
    rv = client.get("/api/stats")
    before = json.loads(rv.data)["total_prompts"]

    # 生成
    client.post(
        "/api/generate",
        data=json.dumps({"products": ["新产品"], "styles": ["北欧简约"]}),
        content_type="application/json",
    )

    # 验证总数增加
    rv = client.get("/api/stats")
    after = json.loads(rv.data)["total_prompts"]
    assert after == before + 1