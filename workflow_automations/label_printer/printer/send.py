"""Low-level printer sender: image -> Brother QL-820NWBc over the network.

Run directly for the Step 1 checkpoint: prints one hardcoded test label.
"""
import os
import sys

from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

PRINTER_IP = os.environ.get("PRINTER_IP")
PRINTER_MODEL = os.environ.get("PRINTER_MODEL", "QL-820NWB")
LABEL_SIZE = os.environ.get("LABEL_SIZE")


def print_image(image: Image.Image, label_size: str = None, printer_ip: str = None, printer_model: str = None):
    """Send a PIL image to the printer. Raises on failure."""
    label_size = label_size or LABEL_SIZE
    printer_ip = printer_ip or PRINTER_IP
    printer_model = printer_model or PRINTER_MODEL

    if not printer_ip:
        raise ValueError("PRINTER_IP not set (env or argument)")
    if not label_size:
        raise ValueError("LABEL_SIZE not set (env or argument) - see brother_ql label code for your loaded stock")

    qlr = BrotherQLRaster(printer_model)
    instructions = convert(
        qlr=qlr,
        images=[image],
        label=label_size,
        rotate="0",
        threshold=70.0,
        dither=False,
        compress=False,
        red=False,
        dpi_600=False,
        hq=True,
        cut=True,
    )
    result = send(
        instructions=instructions,
        printer_identifier=f"tcp://{printer_ip}",
        backend_identifier="network",
        blocking=True,
    )
    return result


def _build_test_image(text: str = "TEST 001") -> Image.Image:
    # 62mm endless roll @ 300dpi is ~696px wide; height is arbitrary for endless stock.
    # Adjust WIDTH/HEIGHT below once the actual label stock (Step 1 checkpoint) is known.
    width, height = 696, 271
    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 60)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - text_w) / 2, (height - text_h) / 2), text, fill=0, font=font)
    return image


if __name__ == "__main__":
    test_text = sys.argv[1] if len(sys.argv) > 1 else "TEST 001"
    img = _build_test_image(test_text)
    print(f"Sending test label ({test_text!r}) to {PRINTER_IP} as {PRINTER_MODEL}, label={LABEL_SIZE}...")
    result = print_image(img)
    print("Result:", result)
