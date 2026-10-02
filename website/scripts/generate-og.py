"""Regenerate the checked-in social preview: python scripts/generate-og.py."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "og.png"
FONT_DIR = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_DIR / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


image = Image.new("RGB", (1200, 630), "#10213b")
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, 16, 630), fill="#3aa6d7")
draw.line((70, 490, 1130, 490), fill="#36536e", width=2)

draw.polygon([(70, 65), (105, 45), (140, 65), (140, 105), (105, 125), (70, 105)], outline="#7dd3fc", width=4)
draw.line([(88, 86), (100, 98), (123, 70)], fill="#ffffff", width=6, joint="curve")
draw.text((159, 53), "verity.", font=font("segoeuib.ttf", 51), fill="#ffffff")
draw.text((70, 224), "One place for the work", font=font("segoeuib.ttf", 61), fill="#ffffff")
draw.text((70, 302), "behind compliance.", font=font("segoeuib.ttf", 61), fill="#ffffff")
draw.text((70, 408), "Controls, assets, vulnerabilities, third-party risk, and evidence.", font=font("segoeui.ttf", 25), fill="#bdd8e7")
draw.text((70, 520), "Verity GRC", font=font("segoeuib.ttf", 19), fill="#8ac9e7")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUTPUT, optimize=True)
print(OUTPUT)
