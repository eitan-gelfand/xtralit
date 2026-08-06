"""Label layout: item name on top (wraps to 2 lines if long), sample/date rows below.

One monday item can produce several physical labels:
- one per sample, numbered 1..N ("N of samples")
- one per selected "Add. samples" category, showing the category name instead
  of a number
"""
from PIL import Image, ImageDraw, ImageFont

# 62mm endless roll (DK-22205) @ 300dpi. Height is a print-length guess for a
# three-line label; adjust after checking against the physical output.
LABEL_WIDTH = 696
LABEL_HEIGHT = 340
MAX_NAME_LINES = 2
NAME_MARGIN = 20  # left/right padding the name must wrap within

NAME_FONT_SIZE = 48
INFO_FONT_SIZE = 40  # shared, constant size for the sample/category row and the date row
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _wrap_to_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int,
                    max_lines: int) -> list[str]:
    """Word-wrap text to at most max_lines, breaking mid-word only if a single word overflows."""
    words = text.split()
    if not words:
        return [text]

    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = word
        else:
            current = word  # single word already too wide; let it overflow rather than break it
        if len(lines) == max_lines - 1:
            break
    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def build_label_image(name: str, subtitle: str, date: str = "") -> Image.Image:
    """Draw item name (top, wraps up to MAX_NAME_LINES), subtitle (sample/category), date."""
    image = Image.new("L", (LABEL_WIDTH, LABEL_HEIGHT), color=255)
    draw = ImageDraw.Draw(image)

    name_font = _load_font(NAME_FONT_SIZE)
    info_font = _load_font(INFO_FONT_SIZE)

    name_lines = _wrap_to_lines(draw, name, name_font, LABEL_WIDTH - 2 * NAME_MARGIN, MAX_NAME_LINES)

    y = 20
    line_gap = 6
    line_heights = []
    for line in name_lines:
        bbox = draw.textbbox((0, 0), line, font=name_font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((LABEL_WIDTH - w) / 2, y), line, fill=0, font=name_font)
        line_heights.append(h)
        y += h + line_gap

    sub_bbox = draw.textbbox((0, 0), subtitle, font=info_font)
    sub_w, sub_h = sub_bbox[2] - sub_bbox[0], sub_bbox[3] - sub_bbox[1]
    sub_y = y + 20
    draw.text(((LABEL_WIDTH - sub_w) / 2, sub_y), subtitle, fill=0, font=info_font)

    if date:
        date_text = f"date: {date}"
        date_bbox = draw.textbbox((0, 0), date_text, font=info_font)
        date_w, date_h = date_bbox[2] - date_bbox[0], date_bbox[3] - date_bbox[1]
        draw.text(((LABEL_WIDTH - date_w) / 2, sub_y + sub_h + 15), date_text, fill=0, font=info_font)

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
        labels.append(build_label_image(name, f"sample: {i}", date))
    for category in fields.get("add_samples", []):
        labels.append(build_label_image(name, category, date))
    return labels
