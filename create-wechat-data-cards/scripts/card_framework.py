from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

BG = "#EEE9DF"
CARD = "#FBFAF6"
GREEN = "#0B4A2F"
DATA_GREEN = "#006837"
GOLD = "#CF8900"
ORANGE = "#C8551A"
INK = "#2F2A22"
GRAY = "#6E6E6E"
LINE = "#D8D1C4"
LIGHT_GREEN = "#DDEDE4"
LIGHT_GOLD = "#F8F2E6"
LIGHT_ORANGE = "#F2D8C8"

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGO = SKILL_ROOT / "assets" / "ag-commodity-logo-transparent.png"


def _font_candidates(bold: bool) -> list[Path]:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = ["msyhbd.ttc", "msyh.ttc"] if bold else ["msyh.ttc", "msyhbd.ttc"]
    candidates = [windows / name for name in names]
    candidates += [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    return candidates


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in _font_candidates(bold):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError("No CJK-capable font found. Install Microsoft YaHei or Noto Sans CJK.")


class CardCanvas:
    """Shared visual foundation for Ag Commodity Research analytical cards."""

    def __init__(self, width: int = 1080, height: int = 1360) -> None:
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.draw.rounded_rectangle((34, 30, width - 34, height - 30), radius=34, fill=CARD)
        self.left = 78
        self.right = width - 78

    def font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return load_font(size, bold)

    def text_width(self, value: str, font: ImageFont.FreeTypeFont) -> int:
        box = self.draw.textbbox((0, 0), value, font=font)
        return box[2] - box[0]

    def centered_text(self, x: float, y: float, value: str, font: ImageFont.FreeTypeFont, fill: str) -> None:
        self.draw.text((x - self.text_width(value, font) / 2, y), value, font=font, fill=fill)

    def wrap(self, value: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in value.splitlines() or [""]:
            current = ""
            for character in paragraph:
                candidate = current + character
                if current and self.text_width(candidate, font) > max_width:
                    lines.append(current)
                    current = character
                else:
                    current = candidate
            lines.append(current)
        return lines

    def wrapped_text(self, xy: tuple[int, int], value: str, font: ImageFont.FreeTypeFont,
                     fill: str, max_width: int, line_gap: int = 8) -> int:
        x, y = xy
        box = self.draw.textbbox((0, 0), "国Ag", font=font)
        line_height = box[3] - box[1]
        for line in self.wrap(value, font, max_width):
            self.draw.text((x, y), line, font=font, fill=fill)
            y += line_height + line_gap
        return y

    def header(self, eyebrow: str, title: str, subtitle: str, logo: Path = DEFAULT_LOGO) -> int:
        self.draw.text((self.left, 68), eyebrow, font=self.font(23, True), fill=GOLD)
        self.wrapped_text((self.left, 113), title, self.font(43, True), GREEN, 680, 5)
        self.draw.text((self.left, 190), subtitle, font=self.font(20), fill=GRAY)
        self.paste_logo(logo, max_size=(230, 86), xy=(self.width - 306, 49))
        self.draw.line((self.left, 236, self.right, 236), fill=LINE, width=2)
        return 268

    def paste_logo(self, logo_path: Path, max_size: tuple[int, int], xy: tuple[int, int]) -> None:
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail(max_size, Image.Resampling.LANCZOS)
        self.image.paste(logo, xy, logo)

    def panel(self, box: tuple[int, int, int, int], fill: str = LIGHT_GOLD, radius: int = 22) -> None:
        self.draw.rounded_rectangle(box, radius=radius, fill=fill)

    def section_heading(self, y: int, title: str, subtitle: str | None = None) -> int:
        self.draw.text((self.left, y), title, font=self.font(29, True), fill=GREEN)
        if subtitle:
            self.draw.text((self.left, y + 42), subtitle, font=self.font(19), fill=GRAY)
            return y + 82
        return y + 48

    def footer(self, lines: Iterable[str], y: int | None = None) -> None:
        lines = list(lines)
        y = y if y is not None else self.height - 82 - 26 * max(1, len(lines))
        for value in lines:
            self.draw.text((self.left, y), value, font=self.font(14), fill=GRAY)
            y += 26

    def save(self, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(output, format="PNG", optimize=True)
        return output


def build_demo(output: Path) -> Path:
    card = CardCanvas()
    y = card.header(
        "MARKET TREND · DEMO",
        "公众号数据卡片：先给结论，再用趋势证明",
        "2017/18—2026/27｜示例数据｜单位需在正式卡片中注明",
    )
    card.panel((78, y, 1002, y + 145), fill=LIGHT_GOLD)
    card.draw.text((106, y + 25), "阅读重点", font=card.font(22, True), fill=ORANGE)
    card.draw.text((106, y + 66), "9.4%", font=card.font(42, True), fill=GREEN)
    card.draw.text((250, y + 78), "必须说明是占总量，还是占预测增量", font=card.font(22, True), fill=INK)

    chart_top = card.section_heading(y + 190, "趋势图示例", "正式制作时替换为经核验的数据，并标出预测区间")
    x0, x1, y0, y1 = 118, 982, chart_top + 35, chart_top + 385
    values = [31, 35, 37, 39, 43, 49, 54, 57, 61, 65]
    for tick in range(20, 81, 20):
        py = y1 - (tick / 80) * (y1 - y0)
        card.draw.line((x0, py, x1, py), fill=LINE, width=2)
        card.draw.text((74, py - 10), str(tick), font=card.font(16), fill=GRAY)
    points = []
    for index, value in enumerate(values):
        px = x0 + index * (x1 - x0) / (len(values) - 1)
        py = y1 - (value / 80) * (y1 - y0)
        points.append((px, py))
        card.draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=DATA_GREEN)
        if index in {0, len(values) - 1}:
            card.centered_text(px, y1 + 16, str(2017 + index), card.font(16), GRAY)
    card.draw.line(points, fill=DATA_GREEN, width=5)
    card.draw.text((points[-1][0] - 55, points[-1][1] - 38), f"{values[-1]}", font=card.font(21, True), fill=DATA_GREEN)

    card.panel((78, y1 + 82, 1002, y1 + 220), fill=LIGHT_GREEN)
    card.draw.text((106, y1 + 108), "表达原则", font=card.font(24, True), fill=GREEN)
    card.draw.text((106, y1 + 151), "标题回答问题；图表提供证据；脚注交代口径与边界。", font=card.font(21, True), fill=INK)
    card.footer(["来源：示例；正式卡片须列明机构、报告/数据集、数据日期与单位。"], y=card.height - 80)
    return card.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ag Commodity Research WeChat card framework")
    parser.add_argument("--demo-output", type=Path, help="Render a self-contained demo card")
    parser.add_argument("--check-assets", action="store_true", help="Check the bundled logo and fonts")
    args = parser.parse_args()
    if args.check_assets:
        if not DEFAULT_LOGO.exists():
            raise FileNotFoundError(DEFAULT_LOGO)
        load_font(20)
        load_font(20, True)
        print("assets_ok")
    if args.demo_output:
        build_demo(args.demo_output)
        print("demo_created")
    if not args.check_assets and not args.demo_output:
        parser.print_help()


if __name__ == "__main__":
    main()