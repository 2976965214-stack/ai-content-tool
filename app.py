# -*- coding: utf-8 -*-
"""AI Content Tool V2 — Flask Web 主入口

V2 升级：
  - SQLite 数据库持久化（替代内存统计）
  - Claude AI API 集成（真实 Prompt 生成）
  - 流式进度接口（SSE）
"""

import os
import uuid
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

import yaml
from flask import (
    Flask, render_template, request, jsonify,
    send_file, url_for, Response, stream_with_context
)

from prompt_generator import (
    read_product_names,
    generate_prompts,
    write_excel,
    write_csv,
    init_ai,
    DEFAULT_STYLES,
)
from image_processor import process_images, create_zip
from database import init_db, save_generation_rows, save_generation_log, save_image_processing, get_all_stats

# ---------------------------------------------------------------
# 配置
# ---------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件
load_dotenv(os.path.join(BASE_DIR, ".env"))

with open(os.path.join(BASE_DIR, "config.yaml"), encoding="utf-8") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
app.config["PROCESSED_FOLDER"] = os.path.join(BASE_DIR, "static", "processed")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

# 内置 styles 列表（从 config 加载）
STYLES = [(s["name"], s["keywords"]) for s in config.get("styles", DEFAULT_STYLES)]

# 初始化数据库
init_db()

# 初始化 AI 客户端（胜算云 OpenAI 兼容格式）
ai_config = config.get("ai", {})
init_ai(
    api_key=os.environ.get("CLAUDE_API_KEY"),
    model=ai_config.get("model", "anthropic/claude-sonnet-4.6"),
    base_url=ai_config.get("base_url", "https://router.shengsuanyun.com/api/v1"),
)
logger.info(f"AI 模式: {'已启用' if os.environ.get('CLAUDE_API_KEY') else '未配置（使用模板生成）'}")


# ---------------------------------------------------------------
# 路由 — 页面
# ---------------------------------------------------------------


@app.route("/")
def index():
    """渲染主页面。"""
    styles_list = [{"name": s[0]} for s in STYLES]
    return render_template(
        "index.html",
        project_name=config.get("app", {}).get("title", "AI Content Tool"),
        styles=styles_list,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ai_enabled=bool(os.environ.get("CLAUDE_API_KEY")),
    )


# ---------------------------------------------------------------
# 路由 — Tab 1: 批量生成
# ---------------------------------------------------------------


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """上传 Excel 文件，返回产品名称列表。"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未选择文件"}), 400
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error": "仅支持 .xlsx 格式"}), 400

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(save_path)

    try:
        products = read_product_names(save_path)
        return jsonify({"products": products, "filename": file.filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """接收产品和风格选择，返回生成的 Prompt 列表。"""
    data = request.get_json()
    products = data.get("products", [])
    selected_styles = data.get("styles", [])
    use_ai = data.get("use_ai", True)

    matched_styles = [s for s in STYLES if s[0] in selected_styles]
    if not matched_styles:
        return jsonify({"error": "请至少选择一个风格"}), 400

    ai_config_local = config.get("ai", {})
    rows = generate_prompts(
        products,
        matched_styles,
        use_ai=use_ai,
    )

    # 保存到数据库
    save_generation_rows(rows)
    for r in rows:
        save_generation_log(r["产品名称"], r["风格"], method=r.get("生成方式", "template"))

    return jsonify({"rows": rows, "total": len(rows)})


@app.route("/api/generate_stream")
def api_generate_stream():
    """SSE 流式生成：逐条返回进度和结果。"""
    products = request.args.getlist("products")
    styles = request.args.getlist("styles")
    use_ai = request.args.get("use_ai", "true") == "true"

    matched_styles = [s for s in STYLES if s[0] in styles]
    if not matched_styles or not products:
        return jsonify({"error": "参数错误"}), 400

    def generate():
        total = len(products) * len(matched_styles)
        current = 0
        all_rows = []

        for product in products:
            for style_name, style_kw in matched_styles:
                current += 1
                method = "template"

                # 尝试 AI 生成
                if use_ai:
                    from prompt_generator import generate_prompt_with_ai
                    ai_config_local = config.get("ai", {})
                    prompt = generate_prompt_with_ai(
                        product, style_name, style_kw,
                        model=ai_config_local.get("model", "claude-sonnet-4-6"),
                        max_tokens=ai_config_local.get("max_tokens", 300),
                        temperature=ai_config_local.get("temperature", 0.7),
                    )
                    if prompt:
                        method = "ai"
                    else:
                        from prompt_generator import generate_single_prompt_template
                        prompt = generate_single_prompt_template(product, style_kw)
                else:
                    from prompt_generator import generate_single_prompt_template
                    prompt = generate_single_prompt_template(product, style_kw)

                from prompt_generator import generate_keywords
                row = {
                    "产品名称": product,
                    "风格": style_name,
                    "Prompt": prompt,
                    "关键词标签": generate_keywords(product, style_name),
                    "生成方式": method,
                }
                all_rows.append(row)

                # 保存日志
                save_generation_log(product, style_name, method=method)

                # SSE 事件
                yield f"data: {json.dumps({'current': current, 'total': total, 'product': product, 'style': style_name, 'method': method})}\n\n"

        # 批量保存生成记录
        save_generation_rows(all_rows)

        # 完成事件
        yield f"data: {json.dumps({'done': True, 'total': total, 'rows': all_rows})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/export", methods=["POST"])
def api_export():
    """导出生成结果为 Excel 或 CSV 文件。"""
    data = request.get_json()
    rows = data.get("rows", [])
    fmt = data.get("format", "excel")

    if not rows:
        return jsonify({"error": "无数据可导出"}), 400

    token = uuid.uuid4().hex[:8]
    if fmt == "csv":
        out_name = f"prompts_{token}.csv"
        out_path = os.path.join(app.config["PROCESSED_FOLDER"], out_name)
        write_csv(rows, out_path)
        mimetype = "text/csv"
    else:
        out_name = f"prompts_{token}.xlsx"
        out_path = os.path.join(app.config["PROCESSED_FOLDER"], out_name)
        write_excel(rows, out_path)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return send_file(out_path, as_attachment=True, download_name=out_name, mimetype=mimetype)


# ---------------------------------------------------------------
# 路由 — Tab 2: 图片处理
# ---------------------------------------------------------------


@app.route("/api/upload_images", methods=["POST"])
def api_upload_images():
    """上传多张图片，返回缩略图 URL 列表。"""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "未选择图片"}), 400

    results = []
    for f in files:
        if not f.filename:
            continue
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
        f.save(save_path)
        results.append({
            "name": f.filename,
            "url": url_for("static", filename=f"uploads/{f.filename}"),
        })

    return jsonify({"images": results})


@app.route("/api/process_images", methods=["POST"])
def api_process_images():
    """处理图片：缩放 + 水印。"""
    data = request.get_json()
    filenames = data.get("images", [])
    width = int(data.get("width", 1080))
    height = int(data.get("height", 1080))
    watermark = data.get("watermark", "")
    opacity = float(data.get("opacity", 0.3))

    if not filenames:
        return jsonify({"error": "请先上传图片"}), 400

    image_paths = [
        os.path.join(app.config["UPLOAD_FOLDER"], fn)
        for fn in filenames
        if os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], fn))
    ]

    results = process_images(
        image_paths,
        target_width=width,
        target_height=height,
        watermark_text=watermark,
        opacity=opacity,
        output_dir=app.config["PROCESSED_FOLDER"],
    )

    # 保存到数据库
    for r in results:
        save_image_processing(
            os.path.basename(r["original_path"]),
            os.path.basename(r["processed_path"]),
            width, height, watermark,
        )

    for r in results:
        r["original_url"] = url_for("static", filename=f"uploads/{os.path.basename(r['original_path'])}")
        r["processed_url"] = url_for("static", filename=f"processed/{os.path.basename(r['processed_path'])}")

    return jsonify({"results": results})


@app.route("/api/download_zip", methods=["POST"])
def api_download_zip():
    """打包处理后图片为 ZIP 下载。"""
    data = request.get_json()
    filenames = data.get("files", [])
    if not filenames:
        return jsonify({"error": "无文件可下载"}), 400

    file_paths = [
        os.path.join(app.config["PROCESSED_FOLDER"], fn)
        for fn in filenames
        if os.path.exists(os.path.join(app.config["PROCESSED_FOLDER"], fn))
    ]

    zip_name = f"processed_{uuid.uuid4().hex[:8]}.zip"
    zip_path = os.path.join(app.config["PROCESSED_FOLDER"], zip_name)
    create_zip(file_paths, zip_path)

    return send_file(zip_path, as_attachment=True, download_name=zip_name, mimetype="application/zip")


# ---------------------------------------------------------------
# 路由 — Tab 3: 数据看板
# ---------------------------------------------------------------


@app.route("/api/stats")
def api_stats():
    """返回统计数据（从数据库读取）。"""
    return jsonify(get_all_stats())


# ---------------------------------------------------------------
# 启动
# ---------------------------------------------------------------

if __name__ == "__main__":
    host = config.get("app", {}).get("host", "127.0.0.1")
    port = config.get("app", {}).get("port", 5000)
    print(f"  AI Content Tool V2 已启动")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  AI 模式: {'启用 (Claude ' + ai_config.get('model', '') + ')' if os.environ.get('CLAUDE_API_KEY') else '未配置（使用模板生成）'}")
    print(f"  数据库: data.db")
    app.run(host=host, port=port, debug=True)