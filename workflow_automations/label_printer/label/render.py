"""Label layout: name + sample/category on one wrapped row, date below.

One monday item can produce several physical labels:
- one per sample, numbered 1..N ("N of samples")
- one per selected "Add. samples" category, showing the category name instead
  of a number

Image height is computed per-label from the actual content, so a short
label (e.g. no wrap, single date line) doesn't carry blank space on the
62mm endless roll.
"""
import re

from PIL import Image, ImageDraw, ImageFont

LABEL_WIDTH = 696  # 62mm endless roll (DK-22205) @ 300dpi
MARGIN = 20  # top/bottom/left/right padding
LINE_GAP = 6
BLOCK_GAP = 20  # gap between the title block and the date line
MAX_TITLE_LINES = 6  # sanity cap against pathological input, not a normal ceiling

NAME_FONT_SIZE = 48
INFO_FONT_SIZE = 40  # subtitle (sample/category) words and the date line

# Bold system font, first match wins. Different install layouts per OS, so
# try the common ones for each rather than hardcoding a single Mac-only path
# (this app is Mac-dev / Windows-distribution). Pillow's own scalable
# built-in font is the last resort - it ships inside Pillow itself, so it's
# always available even if none of these paths exist on a given machine.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
    "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
]

# Splits a word after each hyphen (keeping the hyphen attached to the
# preceding chunk) so long hyphenated codes like "1R-DS-TOE40(106-250)-70(2)-Li"
# - this board's typical item-name shape, with no spaces at all - can still
# wrap instead of running off the edge of the label.
_HYPHEN_SPLIT = re.compile(r"(?<=-)")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _split_oversized_chunk(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                            max_width: int) -> list:
    """Last-resort character-level split for a single chunk still wider than
    max_width on its own (e.g. a long run with no hyphens)."""
    if draw.textlength(text, font=font) <= max_width or len(text) <= 1:
        return [text]
    pieces = []
    current = ""
    for ch in text:
        candidate = current + ch
        if current and draw.textlength(candidate, font=font) > max_width:
            pieces.append(current)
            current = ch
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _tokenize(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Returns [(chunk, font, space_before), ...]. Words are split from
    whitespace (space_before=True for the first chunk of each word) and
    further split at hyphens (space_before=False, no visual gap) so a
    single long hyphenated word can still wrap across lines."""
    tokens = []
    for word in text.split():
        chunks = [c for c in _HYPHEN_SPLIT.split(word) if c]
        for ci, chunk in enumerate(chunks):
            for si, sub in enumerate(_split_oversized_chunk(draw, chunk, font, max_width)):
                tokens.append((sub, font, ci == 0 and si == 0))
    return tokens


def _wrap_tokens(draw: ImageDraw.ImageDraw, tokens: list, max_width: int, max_lines: int) -> list:
    """Greedily wraps pre-tokenized (text, font, space_before) tuples onto
    lines. Never drops content: if max_lines is reached, remaining tokens
    still get appended to the last line rather than silently discarded."""
    lines = []
    current = []
    current_width = 0

    for text, font, space_before in tokens:
        space_width = draw.textlength(" ", font=font) if space_before else 0
        word_width = draw.textlength(text, font=font)
        added_width = word_width + (space_width if current else 0)

        if current and current_width + added_width > max_width and len(lines) < max_lines - 1:
            lines.append(current)
            current = [(text, font, False)]
            current_width = word_width
        else:
            current.append((text, font, space_before if current else False))
            current_width += added_width

    if current:
        lines.append(current)
    return lines


def _line_metrics(draw: ImageDraw.ImageDraw, line: list) -> tuple:
    """Returns (rendered_width, height, max_ascent) for a mixed-font line,
    where height/ascent account for each font's real metrics so words at
    different sizes share one baseline instead of stacking by bbox height."""
    width = 0
    max_ascent = 0
    max_descent = 0
    for text, font, space_before in line:
        space_width = draw.textlength(" ", font=font) if space_before else 0
        w = draw.textlength(text, font=font)
        ascent, descent = font.getmetrics()
        width += w + (space_width if width else 0)
        max_ascent = max(max_ascent, ascent)
        max_descent = max(max_descent, descent)
    return width, max_ascent + max_descent, max_ascent


def _draw_line(draw: ImageDraw.ImageDraw, line: list, y: int, max_ascent: int):
    width, _, _ = _line_metrics(draw, line)
    x = (LABEL_WIDTH - width) / 2
    for text, font, space_before in line:
        if x > (LABEL_WIDTH - width) / 2:
            space_width = draw.textlength(" ", font=font) if space_before else 0
            x += space_width
        ascent, _ = font.getmetrics()
        draw.text((x, y + (max_ascent - ascent)), text, fill=0, font=font)
        x += draw.textlength(text, font=font)


def build_label_image(name: str, subtitle: str, date: str = "") -> Image.Image:
    """Draw '<name> - <subtitle>' as one wrapped row (name at NAME_FONT_SIZE,
    subtitle at INFO_FONT_SIZE), then a date row below. Height fits content."""
    name_font = _load_font(NAME_FONT_SIZE)
    info_font = _load_font(INFO_FONT_SIZE)

    measurer = ImageDraw.Draw(Image.new("L", (1, 1)))
    max_width = LABEL_WIDTH - 2 * MARGIN

    tokens = (
        _tokenize(measurer, name, name_font, max_width)
        + [("-", name_font, True)]
        + _tokenize(measurer, subtitle, info_font, max_width)
    )
    title_lines = _wrap_tokens(measurer, tokens, max_width, MAX_TITLE_LINES)

    y = MARGIN
    line_layout = []  # (line, y, max_ascent)
    for line in title_lines:
        _, line_h, max_ascent = _line_metrics(measurer, line)
        line_layout.append((line, y, max_ascent))
        y += line_h + LINE_GAP
    y += BLOCK_GAP - LINE_GAP

    date_text = f"date: {date}" if date else ""
    if date_text:
        date_ascent, date_descent = info_font.getmetrics()
        date_y = y
        y += date_ascent + date_descent

    total_height = y + MARGIN

    image = Image.new("L", (LABEL_WIDTH, total_height), color=255)
    draw = ImageDraw.Draw(image)

    for line, line_y, max_ascent in line_layout:
        _draw_line(draw, line, line_y, max_ascent)

    if date_text:
        date_w = draw.textlength(date_text, font=info_font)
        draw.text(((LABEL_WIDTH - date_w) / 2, date_y), date_text, fill=0, font=info_font)

    return image


def build_labels_for_item(fields: dict) -> list[Image.Image]:
    """fields: {name, n_samples, add_samples, date} from monday.client.get_item_fields.

    Returns one image per physical label to print: N numbered sample labels,
    then one label per selected Add. samples category.
    """
    name = fields["name"]
    date = fields.get("date", "")
    labels = []
    for i in range(1, fields.get("n_samples", 0) + 1):
        labels.append(build_label_image(name, str(i), date))
    for category in fields.get("add_samples", []):
        labels.append(build_label_image(name, category, date))
    return labels
