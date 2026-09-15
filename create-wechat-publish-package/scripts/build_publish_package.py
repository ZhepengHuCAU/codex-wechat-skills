from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from PIL import Image

BODY_STYLE = (
    "margin:0 0 18px 0;line-height:31px;font-size:16px;color:#262626;"
    "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;"
    "text-align:justify;letter-spacing:.02em;"
)
HEADING_STYLE = (
    "margin:30px 0 18px 0;padding-left:12px;border-left:4px solid #D18A00;"
    "line-height:30px;font-size:21px;font-weight:700;color:#0B4A2F;"
    "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;"
)
IMAGE_STYLE = "display:block;width:100%;height:auto;margin:24px auto 28px auto;"
NOTE_STYLE = (
    "margin:30px 0 0;padding:14px 16px;background:#F6F3EC;border-radius:8px;"
    "line-height:23px;font-size:13px;color:#777;"
    "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;"
)


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b=""):
            digest.update(chunk)
    return digest.hexdigest()


def run_html(paragraph) -> str:
    parts: list[str] = []
    for run in paragraph.runs:
        value = html.escape(run.text).replace("\n", "<br>")
        if not value:
            continue
        if run.bold is True:
            value = f'<strong style="font-weight:700;color:#111;">{value}</strong>'
        if run.italic is True:
            value = f"<em>{value}</em>"
        parts.append(value)
    return "".join(parts) or html.escape(paragraph.text)


def run_markdown(paragraph) -> str:
    parts: list[str] = []
    for run in paragraph.runs:
        value = run.text
        if not value:
            continue
        if run.bold is True:
            value = f"**{value}**"
        if run.italic is True:
            value = f"*{value}*"
        parts.append(value)
    return "".join(parts) or paragraph.text


def is_heading(paragraph) -> bool:
    style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
    if style_name.startswith("heading") or "标题" in style_name:
        return True
    text = paragraph.text.strip()
    nonempty = [run for run in paragraph.runs if run.text.strip()]
    return bool(text and len(text) <= 36 and nonempty and all(run.bold is True for run in nonempty))


def image_blobs(document: Document, paragraph) -> list[tuple[bytes, str]]:
    results: list[tuple[bytes, str]] = []
    for blip in paragraph._p.xpath(".//a:blip"):
        rid = blip.get(qn("r:embed"))
        part = document.part.related_parts[rid]
        subtype = part.content_type.split("/")[-1].lower()
        extension = "jpg" if subtype in {"jpeg", "jpg"} else subtype
        if extension not in {"png", "jpg", "gif", "webp"}:
            extension = "png"
        results.append((part.blob, extension))
    return results


def safe_image_label(value: str) -> str:
    forbidden = '<>:"/\\|?*'
    cleaned = "".join("_" if char in forbidden else char for char in value).strip(" ._")
    return cleaned[:48] or "插图"


def build(args: argparse.Namespace) -> tuple[Path, Path]:
    source = args.source.resolve()
    output = args.output.resolve()
    zip_path = output.parent / f"{output.name}.zip"
    if output.exists() or zip_path.exists():
        raise FileExistsError("Output package or ZIP already exists; choose a new versioned output path.")
    if not source.exists():
        raise FileNotFoundError(source)

    output.mkdir(parents=True)
    images_dir = output / "images"
    images_dir.mkdir()
    if args.cover:
        cover_dir = output / "cover"
        cover_dir.mkdir()
        for item in args.cover:
            shutil.copy2(item, cover_dir / item.name)

    document = Document(source)
    html_parts = [
        '<section data-role="wechat-article" '
        'style="width:100%;max-width:none;margin:0;padding:0;box-sizing:border-box;">'
    ]
    markdown_parts: list[str] = []
    text_parts: list[str] = []
    image_records: list[dict[str, object]] = []
    image_titles = list(args.image_title or [])
    first_rendered = True
    skipped_title = False

    for paragraph_index, paragraph in enumerate(document.paragraphs):
        value = paragraph.text.strip()
        if args.skip_first_title and not skipped_title and value:
            skipped_title = True
            continue
        if not skipped_title and value == args.title.strip():
            skipped_title = True
            continue

        blobs = image_blobs(document, paragraph)
        for blob, extension in blobs:
            order = len(image_records) + 1
            label = image_titles[order - 1] if order <= len(image_titles) else f"插图{order}"
            filename = f"{order:02d}_{safe_image_label(label)}.{extension}"
            image_path = images_dir / filename
            image_path.write_bytes(blob)
            with Image.open(BytesIO(blob)) as source_image:
                width, height = source_image.size
            image_records.append({
                "order": order,
                "paragraph_index": paragraph_index,
                "file": f"images/{filename}",
                "width": width,
                "height": height,
                "bytes": len(blob),
            })
            image_style = IMAGE_STYLE if not first_rendered else IMAGE_STYLE.replace("margin:24px", "margin:0")
            html_parts.append(
                f'<p style="margin:0;padding:0;"><img src="images/{html.escape(filename)}" '
                f'alt="{html.escape(label)}" style="{image_style}"></p>'
            )
            markdown_parts.append(f"![{label}](images/{filename})")
            text_parts.append(f"【插图{order}：{label}】")
            first_rendered = False

        if not value:
            continue
        if is_heading(paragraph):
            style = HEADING_STYLE if not first_rendered else HEADING_STYLE.replace("margin:30px", "margin:0")
            html_parts.append(f'<h2 style="{style}">{html.escape(value)}</h2>')
            markdown_parts.append(f"## {run_markdown(paragraph)}")
        else:
            html_parts.append(f'<p style="{BODY_STYLE}">{run_html(paragraph)}</p>')
            markdown_parts.append(run_markdown(paragraph))
        text_parts.append(value)
        first_rendered = False

    if image_titles and len(image_titles) != len(image_records):
        raise ValueError(f"Expected {len(image_titles)} images from --image-title, found {len(image_records)}")

    sources_text = args.sources_file.read_text(encoding="utf-8-sig").strip() if args.sources_file else "请补充公开数据来源与数据日期。"
    note = html.escape(args.note).replace("\n", "<br>") if args.note else "本文涉及的情景测算不代表官方预测，亦不构成投资建议。"
    source_note_html = (
        f'<section style="{NOTE_STYLE}">'
        f'<p style="margin:0 0 6px;"><strong>数据来源：</strong>{html.escape(sources_text)}</p>'
        f'<p style="margin:0;"><strong>说明：</strong>{note}</p></section>'
    )
    html_parts.extend([source_note_html, "</section>"])
    fragment = "\n".join(html_parts)
    preview = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(args.title)}</title>
<style>
body{{margin:0;background:#f3f0e8;}}
.page{{width:100%;max-width:none;margin:0;padding:0;background:#fff;box-sizing:border-box;}}
</style></head><body><main class="page">{fragment}</main></body></html>'''

    cover_status = bool(args.cover)
    write_text(output / "01_发布信息.txt", (
        f"标题：{args.title}\n作者：{args.author}\n摘要：{args.digest}\n"
        f"原文链接：{args.source_url or '未提供'}\n封面：{'已包含' if cover_status else '不包含'}\n"
    ))
    write_text(output / "02_公众号正文_可粘贴.html", preview)
    write_text(output / "02A_公众号正文_HTML片段.html", fragment)
    write_text(output / "03_公众号正文_带图片.md", "\n\n".join(markdown_parts) + f"\n\n---\n\n**数据来源：** {sources_text}\n\n**说明：** {args.note}\n")
    write_text(output / "04_公众号正文_纯文本.txt", "\n\n".join(text_parts) + f"\n\n数据来源：{sources_text}\n")

    metadata = {
        "title": args.title,
        "author": args.author,
        "digest": args.digest,
        "content_source_url": args.source_url,
        "cover_included": cover_status,
        "body_title_included": False,
        "source_docx": source.name,
        "image_count": len(image_records),
        "images": image_records,
        "suggested_alternative_titles": list(args.alternative_title or []),
    }
    write_text(output / "05_发布信息.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    write_text(output / "06_数据来源.md", "# 数据来源\n\n" + sources_text + "\n")
    shutil.copy2(source, output / source.name)

    readme = f'''# 公众号发布包使用说明

本包对应文章《{args.title}》。

## 导入

1. 在公众号后台新建图文消息。
2. 按 `01_发布信息.txt` 填写标题、作者、摘要和原文链接。
3. 打开 `02_公众号正文_可粘贴.html`，复制页面正文并粘贴到编辑器。
4. 如果本地图片没有随复制进入编辑器，按 `images` 文件夹的编号顺序手动上传并插入。这是浏览器对 `file://` 图片的正常限制。
5. 检查正文不重复文章标题，图片共 {len(image_records)} 张且顺序正确。
6. 保存草稿并进行手机预览。此发布包生成过程不会自动保存草稿、群发或发布。

`02A_公众号正文_HTML片段.html` 供支持源码导入的编辑工具使用；`03` 和 `04` 是后备版本；`manifest.json` 用于完整性核验。
'''
    write_text(output / "README_发布说明.md", readme)

    files: list[dict[str, object]] = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        record: dict[str, object] = {
            "file": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            with Image.open(path) as source_image:
                record["width"] = source_image.width
                record["height"] = source_image.height
        files.append(record)
    write_text(output / "manifest.json", json.dumps({
        "package": output.name,
        "created_for": "WeChat Official Account manual import",
        "cover_included": cover_status,
        "manifest_excludes_itself": True,
        "files": files,
    }, ensure_ascii=False, indent=2))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in output.rglob("*") if item.is_file()):
            archive.write(path, Path(output.name) / path.relative_to(output))
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP integrity check failed: {bad}")
    return output, zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a complete WeChat Official Account publishing package from DOCX")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", default="Ag Commodity Research")
    parser.add_argument("--digest", required=True)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--sources-file", type=Path)
    parser.add_argument("--note", default="本文涉及的情景测算不代表官方预测，亦不构成投资建议。")
    parser.add_argument("--alternative-title", action="append")
    parser.add_argument("--image-title", action="append", help="Repeat in embedded-image order")
    parser.add_argument("--cover", type=Path, action="append")
    parser.add_argument("--skip-first-title", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
    print("package_created")
