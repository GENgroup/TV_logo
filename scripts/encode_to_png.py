"""
Кодирует произвольный UTF-8 текст (обычно JSON) в PNG-картинку.

Схема (не менять - под неё заточен декодер в final-work.html):
- каждый байт = 2 ниббла (старший, младший)
- каждый ниббл (0-15) хранится как яркость пикселя = ниббл * 17
- 3 ниббл-слота на пиксель (R, G, B), высота картинки = 1 пиксель
- первые 4 байта = длина текста (big-endian uint32), дальше сам текст
"""
from PIL import Image


def encode_text_to_png(text: str, out_path: str):
    payload = text.encode("utf-8")
    length = len(payload)
    header = bytes([
        (length >> 24) & 0xFF,
        (length >> 16) & 0xFF,
        (length >> 8) & 0xFF,
        length & 0xFF,
    ])
    all_bytes = header + payload

    nibbles = []
    for b in all_bytes:
        nibbles.append((b >> 4) & 0xF)
        nibbles.append(b & 0xF)

    while len(nibbles) % 3 != 0:
        nibbles.append(0)

    width = len(nibbles) // 3
    img = Image.new("RGB", (width, 1))
    px = img.load()
    for x in range(width):
        r, g, b = nibbles[x * 3], nibbles[x * 3 + 1], nibbles[x * 3 + 2]
        px[x, 0] = (r * 17, g * 17, b * 17)
    img.save(out_path)
    return width, length
