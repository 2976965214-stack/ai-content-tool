# -*- coding: utf-8 -*-
"""Prompt 生成模块 — 从 Excel 读取产品名称，生成英文生图 Prompt。

V2 升级：集成 Claude API 实现 AI 真实生成，失败时自动降级为模板拼接。
"""

import os
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dotenv import load_dotenv

import pandas as pd

logger = logging.getLogger(__name__)

# 加载 .env 文件
load_dotenv()


# 默认风格定义（作为后备，实际风格由调用方传入）
DEFAULT_STYLES: List[Tuple[str, str]] = [
    ("北欧简约", "Scandinavian minimalism, clean lines, neutral color palette, natural lighting, uncluttered composition, soft shadows, aesthetic and serene atmosphere"),
    ("科技感", "Futuristic tech style, neon accents, dark background with blue/purple glow, sleek metallic surfaces, HUD interface elements, high contrast, cyberpunk aesthetic"),
    ("日常场景", "Realistic everyday use scene, natural indoor lighting, candid lifestyle shot, warm atmosphere, genuine human interaction, photorealistic texture"),
    ("电商白底", "E-commerce white background, 360 degree studio lighting, pure white backdrop, sharp focus, commercial product photography, high-res detail, clean reflection on surface"),
    ("户外使用", "Outdoor adventure setting, golden hour sunlight, nature backdrop, dynamic action shot, deep depth of field, atmospheric sky, vibrant natural colors"),
]


COLUMN_PRODUCT_NAME = "产品名称"


def read_product_names(filepath: str) -> List[str]:
    """
    从 Excel 文件中读取产品名称列。

    参数:
        filepath: Excel 文件路径

    返回:
        产品名称字符串列表
    """
    df = pd.read_excel(filepath, engine="openpyxl")
    if COLUMN_PRODUCT_NAME not in df.columns:
        raise ValueError(f"Excel 文件中找不到列 '{COLUMN_PRODUCT_NAME}'。现有列: {list(df.columns)}")
    products = df[COLUMN_PRODUCT_NAME].dropna().astype(str).str.strip().tolist()
    products = [p for p in products if p]
    if not products:
        raise ValueError(f"'{COLUMN_PRODUCT_NAME}' 列没有有效数据。")
    return products


def generate_single_prompt_template(product: str, style_keywords: str) -> str:
    """
    模板方式生成 Prompt（降级方案）。

    参数:
        product:        产品名称
        style_keywords: 风格英文关键词描述

    返回:
        完整的英文 Prompt
    """
    return (
        f"Product photography of a {product}, "
        f"{style_keywords}. "
        f"High quality, 8K, detailed texture, professional lighting, "
        f"shot on Hasselblad X1D II 50C, cinematic composition."
    )


def generate_keywords(product: str, style_name: str) -> str:
    """
    生成英文关键词标签。

    参数:
        product:    产品名称
        style_name: 风格名称

    返回:
        逗号分隔的关键词字符串
    """
    product_en = product.replace(" ", "_")
    style_en = style_name.replace(" ", "_")
    return f"{product_en}, {style_en}, product_photography, 8K, commercial"


# ============================================================
# AI API 集成（兼容 OpenAI 格式，适配胜算云等第三方平台）
# ============================================================

_ai_client = None
_ai_enabled = False
_ai_base_url = "https://router.shengsuanyun.com/api/v1"


def init_ai(api_key: Optional[str] = None, model: str = "anthropic/claude-sonnet-4.6", base_url: Optional[str] = None) -> None:
    """
    初始化 AI 客户端（OpenAI 兼容格式）。

    参数:
        api_key:  API Key，默认从环境变量 CLAUDE_API_KEY 读取
        model:    模型名称
        base_url: API 请求地址，默认使用胜算云地址
    """
    global _ai_client, _ai_enabled, _ai_base_url
    key = api_key or os.environ.get("CLAUDE_API_KEY", "")
    if base_url:
        _ai_base_url = base_url

    if not key:
        logger.warning("未设置 CLAUDE_API_KEY，将使用模板模式生成 Prompt")
        _ai_enabled = False
        return

    try:
        from openai import OpenAI
        _ai_client = OpenAI(api_key=key, base_url=_ai_base_url)
        _ai_enabled = True
        logger.info(f"AI 客户端初始化成功，端点: {_ai_base_url}，模型: {model}")
    except Exception as e:
        logger.warning(f"AI 客户端初始化失败: {e}，将使用模板模式")
        _ai_enabled = False


def generate_prompt_with_ai(
    product: str,
    style_name: str,
    style_keywords: str,
    model: str = "anthropic/claude-sonnet-4.6",
    max_tokens: int = 300,
    temperature: float = 0.7,
) -> Optional[str]:
    """
    调用 AI API（OpenAI 兼容格式）生成英文生图 Prompt。

    参数:
        product:       产品名称
        style_name:    风格名称
        style_keywords: 风格关键词
        model:         模型名称
        max_tokens:    最大生成长度
        temperature:   生成温度

    返回:
        生成的 Prompt 字符串，失败返回 None
    """
    if not _ai_enabled or not _ai_client:
        return None

    system_prompt = (
        "You are a professional AI image prompt engineer. "
        "Generate high-quality English prompts for product photography. "
        "Output ONLY the prompt text, no explanations, no markdown."
    )

    user_prompt = (
        f"Generate a detailed English prompt for product photography of '{product}' "
        f"in the style of '{style_name}'. "
        f"Style keywords: {style_keywords}. "
        f"The prompt should be vivid, photorealistic, and suitable for AI image generation. "
        f"Include lighting, composition, background, mood, and camera details."
    )

    try:
        response = _ai_client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI 生成失败 (product={product}, style={style_name}): {e}")
        return None


def generate_prompts(
    products: List[str],
    selected_styles: List[Tuple[str, str]],
    use_ai: bool = True,
    progress_callback: Optional[Callable] = None,
) -> List[Dict[str, str]]:
    """
    为每个产品 + 每个选中风格生成 Prompt。

    支持 AI 生成（优先）和模板生成（降级）。
    支持逐条进度回调。

    参数:
        products:         产品名称列表
        selected_styles:  选中的风格列表，每项为 (名称, 关键词)
        use_ai:           是否使用 AI 生成
        progress_callback: 进度回调函数 (current, total, product, style)

    返回:
        字典列表，每项含 产品名称 / 风格 / Prompt / 关键词标签
    """
    rows = []
    total = len(products) * len(selected_styles)
    current = 0

    for product in products:
        for style_name, style_kw in selected_styles:
            current += 1

            if progress_callback:
                progress_callback(current, total, product, style_name)

            prompt = None
            method = "template"

            # 优先用 AI 生成
            if use_ai and _ai_enabled:
                prompt = generate_prompt_with_ai(product, style_name, style_kw)
                if prompt:
                    method = "ai"

            # 降级到模板
            if not prompt:
                prompt = generate_single_prompt_template(product, style_kw)

            rows.append({
                "产品名称": product,
                "风格": style_name,
                "Prompt": prompt,
                "关键词标签": generate_keywords(product, style_name),
                "生成方式": method,
            })

    return rows


def write_excel(rows: List[Dict[str, str]], output_path: str) -> None:
    """
    将结果写入 Excel 文件。

    参数:
        rows:        数据行列表
        output_path: 输出文件路径
    """
    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False, engine="openpyxl")


def write_csv(rows: List[Dict[str, str]], output_path: str) -> None:
    """
    将结果写入 CSV 文件（UTF-8 BOM 以兼容 Excel 打开中文）。

    参数:
        rows:        数据行列表
        output_path: 输出文件路径
    """
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")