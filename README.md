# AI Content Tool V2

> 智能内容生产管理平台 — 批量生成英文生图 Prompt、图片处理、数据可视化看板
> 集成 Claude AI 大模型 + SQLite 持久化 + ECharts 看板 + 单元测试

## 功能

| 模块 | 功能 |
|------|------|
| **批量生成** | 上传 Excel → 选择风格 → Claude AI 生成英文 Prompt → 导出 Excel/CSV |
| **图片处理** | 多图上传 → 缩放 + 水印 → 前后对比 → ZIP 打包 |
| **数据看板** | ECharts 柱状图/饼图/折线图 + 三色统计卡片 |

## 快速启动

```bash
pip install -r requirements.txt
python app.py
# 打开 http://127.0.0.1:5000
```

## 技术栈

Python Flask · SQLite · Pillow · ECharts · Claude API · Docker · GitHub Actions CI

## 测试

```bash
pytest -v  # 11 passed
```
