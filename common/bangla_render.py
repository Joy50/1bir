"""Correct Bengali rendering for ReportLab PDFs.

ReportLab's HarfBuzz text path does not preserve mark positioning for Bengali
when fonts are subset into PDF. Drawing shaped glyphs as vector outlines keeps
conjuncts and dependent vowels intact.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import uharfbuzz
from fontTools.pens.reportLabPen import ReportLabPen
from fontTools.ttLib import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import freshTTFont
from reportlab.platypus import Flowable

FONT_NAME = "Kalpurush"
FONT_CANDIDATES = [
    Path(__file__).resolve().parent / "fonts" / "kalpurush.ttf",
    Path(r"C:\Windows\Fonts\kalpurush.ttf"),
]
HB_FEATURES = {
    "kern": True,
    "liga": True,
    "clig": True,
    "calt": True,
    "mark": True,
    "mkmk": True,
}


def _font_path() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("Kalpurush font file not found")


def register_bangla_font() -> str:
    path = _font_path()
    try:
        pdfmetrics.getFont(FONT_NAME).unregister()
    except Exception:
        pass
    pdfmetrics.registerFont(freshTTFont(FONT_NAME, str(path), shapable=False))
    return FONT_NAME


@lru_cache(maxsize=1)
def _font_blob() -> bytes:
    return _font_path().read_bytes()


@lru_cache(maxsize=1)
def _tt_font() -> TTFont:
    return TTFont(BytesIO(_font_blob()))


@lru_cache(maxsize=1)
def _hb_face() -> uharfbuzz.Face:
    return uharfbuzz.Face(uharfbuzz.Blob(_font_blob()))


@lru_cache(maxsize=8)
def _hb_font(font_size: float) -> uharfbuzz.Font:
    font = uharfbuzz.Font(_hb_face())
    font.scale = (_hb_face().upem, _hb_face().upem)
    font.ptem = font_size
    return font


@dataclass(frozen=True)
class _GlyphRun:
    glyph_name: str
    x_offset: float
    y_offset: float
    x_advance: float


@dataclass(frozen=True)
class _ShapedLine:
    runs: tuple[_GlyphRun, ...]
    width: float


def _scale(value: float, font_size: float) -> float:
    return value * font_size / _hb_face().upem


def _shape_text(text: str, font_size: float) -> list[_GlyphRun]:
    if not text:
        return []
    buf = uharfbuzz.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    uharfbuzz.shape(_hb_font(font_size), buf, HB_FEATURES)
    hbf = _hb_font(font_size)
    runs: list[_GlyphRun] = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        runs.append(
            _GlyphRun(
                glyph_name=hbf.glyph_to_string(info.codepoint),
                x_offset=_scale(pos.x_offset, font_size),
                y_offset=_scale(pos.y_offset, font_size),
                x_advance=_scale(pos.x_advance, font_size),
            )
        )
    return runs


def measure_bangla_text(text: str, font_size: float) -> float:
    return sum(run.x_advance for run in _shape_text(text, font_size))


def _draw_glyph(canvas, glyph_name: str, x: float, y: float, font_size: float) -> None:
    glyph_set = _tt_font().getGlyphSet()
    if glyph_name not in glyph_set:
        return
    from reportlab.lib import colors

    fill = getattr(canvas, "_fillColorObj", (0, 0, 0))
    if isinstance(fill, tuple):
        fill = colors.Color(*fill)
    from reportlab.graphics.shapes import _renderPath

    pen = ReportLabPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    path = pen.path
    scale = font_size / _hb_face().upem
    pdf_path = canvas.beginPath()
    draw_funcs = (pdf_path.moveTo, pdf_path.lineTo, pdf_path.curveTo, pdf_path.close)
    canvas.saveState()
    canvas.setFillColor(fill)
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    _renderPath(path, draw_funcs, forceClose=1)
    canvas.drawPath(pdf_path, fill=1, stroke=0)
    canvas.restoreState()


def draw_bangla_text(canvas, text: str, x: float, y: float, font_size: float) -> float:
    cursor = x
    for run in _shape_text(text, font_size):
        draw_x = cursor + run.x_offset
        draw_y = y + run.y_offset
        _draw_glyph(canvas, run.glyph_name, draw_x, draw_y, font_size)
        cursor += run.x_advance
    return cursor - x


def draw_centred_bangla_text(canvas, x: float, y: float, text: str, font_size: float) -> None:
    width = measure_bangla_text(text, font_size)
    draw_bangla_text(canvas, text, x - width / 2, y, font_size)


def _line_width(text: str, font_size: float) -> float:
    return measure_bangla_text(text, font_size)


def _wrap_line(text: str, max_width: float, font_size: float) -> list[str]:
    text = text.strip()
    if not text:
        return [""]
    if _line_width(text, font_size) <= max_width:
        return [text]
    words = text.split()
    if len(words) <= 1:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _line_width(candidate, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _shape_line(text: str, font_size: float) -> _ShapedLine:
    runs = tuple(_shape_text(text, font_size))
    return _ShapedLine(runs, sum(run.x_advance for run in runs))


class BanglaText(Flowable):
    """Flowable paragraph replacement for Bengali text."""

    def __init__(self, text, font_size=10, leading=14, align=TA_LEFT):
        super().__init__()
        self.text = str(text or "")
        self.font_size = font_size
        self.leading = leading
        self.align = align
        self._lines: list[_ShapedLine] = []

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self._lines = []
        for raw in self.text.replace("<br/>", "\n").split("\n"):
            for chunk in _wrap_line(raw, availWidth, self.font_size):
                self._lines.append(_shape_line(chunk, self.font_size))
        if not self._lines:
            self._lines = [_ShapedLine((), 0.0)]
        self.height = len(self._lines) * self.leading
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        y = self.height - self.font_size
        for line in self._lines:
            if self.align == TA_CENTER:
                x = (self.width - line.width) / 2
            elif self.align == TA_RIGHT:
                x = self.width - line.width
            else:
                x = 0
            cursor = x
            for run in line.runs:
                draw_x = cursor + run.x_offset
                draw_y = y + run.y_offset
                _draw_glyph(canvas, run.glyph_name, draw_x, draw_y, self.font_size)
                cursor += run.x_advance
            y -= self.leading


def bangla_paragraph(text, font_size=10, leading=14, align=TA_LEFT):
    return BanglaText(text, font_size, leading, align)

