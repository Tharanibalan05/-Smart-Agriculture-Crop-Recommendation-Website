"""
Generate 192x192 and 512x512 PWA icons for Smart Agriculture using PIL.
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_pwa_icon(size: int, filename: str):
    # Dark background matching app theme (#111827)
    img = Image.new("RGBA", (size, size), color=(17, 24, 39, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer emerald green rounded glow circle (#10b981)
    padding = size // 8
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=(16, 185, 129, 255),
        outline=(52, 211, 153, 255),
        width=max(2, size // 64)
    )
    
    # Inner dark accent circle
    inner_pad = padding + (size // 12)
    draw.ellipse(
        [inner_pad, inner_pad, size - inner_pad, size - inner_pad],
        fill=(17, 24, 39, 255)
    )
    
    # Simple leaf / plant shape in emerald green
    cx, cy = size // 2, size // 2
    rw = size // 6
    rh = size // 4
    
    # Main leaf outline / fill
    draw.polygon(
        [
            (cx, cy - rh),
            (cx + rw, cy),
            (cx, cy + rh),
            (cx - rw, cy)
        ],
        fill=(16, 185, 129, 255)
    )
    
    # Leaf stem
    draw.line(
        [(cx, cy - rh), (cx, cy + rh + (size // 16))],
        fill=(255, 255, 255, 230),
        width=max(2, size // 48)
    )
    
    img.save(filename, "PNG")
    print(f"Saved PWA icon: {filename} ({size}x{size})")

if __name__ == "__main__":
    create_pwa_icon(192, "icon-192.png")
    create_pwa_icon(512, "icon-512.png")
