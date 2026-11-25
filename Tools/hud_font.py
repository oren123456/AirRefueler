"""Writes Data/Generated/T_HUDFont.png: 8x8 atlas (64 px cells) of ASCII 32..95 in DejaVu Sans Mono, white on black.
Cell index = code - 32, row-major from top-left. Imported by Content/Python/hud_setup.py."""
import os
from PIL import Image, ImageDraw, ImageFont
F = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
font = ImageFont.truetype(F, 46)
im = Image.new("L", (512, 512), 0); d = ImageDraw.Draw(im)
for i in range(64):
    ch = chr(32 + i); cx, cy = (i % 8) * 64 + 32, (i // 8) * 64 + 32
    d.text((cx, cy), ch, fill=255, font=font, anchor="mm")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "Generated", "T_HUDFont.png")
im.save(out); print("->", out)
