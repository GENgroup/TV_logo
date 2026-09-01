"""
Кодирует произвольный UTF-8 текст (обычно JSON) в PNG-картинку.

Схема (не менять - под неё заточен декодер в final-work.html):
- каждый байт = 2 ниббла (старший, младший)
- каждый ниббл (0-15) хранится как яркость пикселя = ниббл * 17
- 3 ниббл-слота на пиксель (R, G, B)
- картинка - ПРЯМОУГОЛЬНИК (не однопиксельная полоса!) - ширина ограничена
  max_width, чтобы не упереться в лимиты браузера на размер canvas
- заполнение построчное (row-major): пиксель с индексом i имеет
  координаты x = i % width, y = i // width - именно в таком порядке
  ImageData отдаёт браузер, декодер этим пользуется
- первые 4 байта = длина текста (big-endian uint32), дальше сам текст
"""
import math
from PIL import Image


def encode_text_to_png(text: str, out_path: str, max_width: int = 2000):
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

    total_pixels = len(nibbles) // 3
    width = min(max_width, max(total_pixels, 1))
    height = max(1, math.ceil(total_pixels / width))

    img = Image.new("RGB", (width, height))
    px = img.load()
    for i in range(total_pixels):
        x = i % width
        y = i // width
        r, g, b = nibbles[i * 3], nibbles[i * 3 + 1], nibbles[i * 3 + 2]
        px[x, y] = (r * 17, g * 17, b * 17)
    img.save(out_path)
    return width, height, length
