# -*- coding: utf-8 -*-
"""图片处理模块 — 缩放、水印、打包下载。"""

import os
import zipfile
from typing import List, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance


def resize_image(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """
    将图片等比例缩放并填充/裁切到目标尺寸。

    策略：先等比例缩放至能覆盖目标尺寸，再居中裁切。

    参数:
        img:           PIL Image 对象
        target_width:  目标宽度
        target_height: 目标高度

    返回:
        处理后的 PIL Image 对象（RGB 模式）
    """
    img = img.convert("RGB")
    src_w, src_h = img.size
    ratio = max(target_width / src_w, target_height / src_h)
    new_w = int(src_w * ratio)
    new_h = int(src_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2
    img = img.crop((left, top, left + target_width, top + target_height))
    return img


def add_watermark(img: Image.Image, text: str, opacity: float = 0.3) -> Image.Image:
    """
    在图片右下角添加半透明水印文字。

    参数:
        img:     PIL Image 对象
        text:    水印文字
        opacity: 透明度 (0.0 ~ 1.0)

    返回:
        添加水印后的 PIL Image 对象
    """
    from PIL import ImageFilter

    img = img.convert("RGBA")

    # 创建水印层
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # 动态计算字号（图片宽度的 1/30）
    font_size = max(20, img.width // 30)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # 测量文字尺寸
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # 位置：右下角，留 20px 边距
    margin = 20
    x = img.width - tw - margin
    y = img.height - th - margin

    draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))

    result = Image.alpha_composite(img, txt_layer).convert("RGB")
    return result


def process_images(
    image_paths: List[str],
    target_width: int = 1080,
    target_height: int = 1080,
    watermark_text: str = "",
    opacity: float = 0.3,
    output_dir: str = "processed",
) -> List[Dict[str, str]]:
    """
    批量处理图片：缩放 + 可选水印。

    参数:
        image_paths:   原始图片路径列表
        target_width:  目标宽度
        target_height: 目标高度
        watermark_text: 水印文字（为空则不添加水印）
        opacity:        水印透明度
        output_dir:     输出目录

    返回:
        字典列表，每项含 original_path / processed_path / original_url / processed_url
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []

    for path in image_paths:
        basename = os.path.basename(path)
        name, ext = os.path.splitext(basename)
        out_name = f"{name}_processed{ext}"
        out_path = os.path.join(output_dir, out_name)

        img = Image.open(path)
        img = resize_image(img, target_width, target_height)

        if watermark_text:
            img = add_watermark(img, watermark_text, opacity)

        img.save(out_path, quality=95)

        results.append({
            "original_path": path,
            "processed_path": out_path,
            "original_url": f"/uploads/{basename}",
            "processed_url": f"/processed/{out_name}",
        })

    return results


def create_zip(file_paths: List[str], zip_path: str) -> str:
    """
    将指定文件打包为 ZIP。

    参数:
        file_paths: 要打包的文件路径列表
        zip_path:   目标 ZIP 文件路径

    返回:
        ZIP 文件路径
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            if os.path.exists(fp):
                zf.write(fp, os.path.basename(fp))
    return zip_path
