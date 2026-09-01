"""
ЕДИНЫЙ скрипт сборки данных плеера GEN-tv.
Раньше было 3 отдельных файла (encode_to_png.py, build_channels_png.py,
build_epg_png.py) - из-за путаницы при копипасте они постоянно менялись
местами. Теперь всё в одном файле - путать физически нечего.

Запуск:
    python build_all.py              -> пересобрать И список каналов, И EPG
    python build_all.py channels-only -> пересобрать ТОЛЬКО список каналов
"""
import gzip
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_SRC = ROOT / "channels-list.json"
CHANNELS_OUT = ROOT / "channels-data.png"
EPG_OUT = ROOT / "epg-data.png"

EPG_SOURCE_URL = "http://programtv.ru/xmltv.xml.gz/491676941"

CHANNEL_RE = re.compile(
    r'<channel id="(\d+)">\s*<display-name>(.*?)</display-name>', re.S
)
PROG_RE = re.compile(
    r'<programme start="([^"]+)" stop="([^"]+)" channel="(\d+)">\s*'
    r'<title>(.*?)</title>', re.S
)


def encode_text_to_png(text, out_path, max_width=2000):
    payload = text.encode("utf-8")
    length = len(payload)
    header = bytes([
        (length >> 24) & 0xFF, (length >> 16) & 0xFF,
        (length >> 8) & 0xFF, length & 0xFF,
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
        x, y = i % width, i // width
        r, g, b = nibbles[i*3], nibbles[i*3+1], nibbles[i*3+2]
        px[x, y] = (r*17, g*17, b*17)
    img.save(out_path)
    return width, height, length


def unescape(s):
    return (s.replace("&quot;", '"').replace("&amp;", "&")
             .replace("&#039;", "'").replace("&lt;", "<").replace("&gt;", ">"))


def build_channels():
    if not CHANNELS_SRC.exists():
        print(f"ОШИБКА: не найден {CHANNELS_SRC}")
        return False

    text = CHANNELS_SRC.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ОШИБКА: {CHANNELS_SRC.name} - невалидный JSON, картинка НЕ пересобрана.")
        print(f"Подробности: {e}")
        return False

    groups = data.get("groups", [])
    total_items = sum(len(g.get("items", [])) for g in groups)
    print(f"[каналы] Групп: {len(groups)}, каналов всего: {total_items}")

    w, h, length = encode_text_to_png(text, str(CHANNELS_OUT))
    print(f"[каналы] OK: {CHANNELS_OUT.name} собран - {w}x{h} px, {length} байт")
    return True


def build_epg():
    print(f"[epg] Качаю: {EPG_SOURCE_URL}")

    raw = None
    last_error = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(EPG_SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                expected = resp.headers.get("Content-Length")
                if expected is not None and int(expected) != len(raw):
                    raise IOError(f"скачано {len(raw)} байт, обещано {expected} - обрыв")
            gzip.decompress(raw)
            break
        except Exception as e:
            last_error = e
            print(f"[epg] Попытка {attempt}/3 не удалась: {e}")
            raw = None
            time.sleep(5)

    if raw is None:
        print(f"[epg] ОШИБКА: не удалось скачать источник за 3 попытки - {last_error}")
        return False

    text = gzip.decompress(raw).decode("utf-8")
    channels = dict(CHANNEL_RE.findall(text))
    print(f"[epg] Каналов в источнике: {len(channels)}")

    epg = {}
    seen = set()
    dup_count = 0
    for start, stop, chid, title in PROG_RE.findall(text):
        name = channels.get(chid)
        if not name:
            continue
        key = (chid, start)
        if key in seen:
            dup_count += 1
            continue
        seen.add(key)
        epg.setdefault(name, []).append({
            "start": start, "stop": stop, "title": unescape(title.strip())
        })
    for name in epg:
        epg[name].sort(key=lambda p: p["start"])

    total = sum(len(v) for v in epg.values())
    print(f"[epg] Каналов с расписанием: {len(epg)}, передач: {total} (повторов убрано: {dup_count})")

    if not epg:
        print("[epg] ОШИБКА: расписание пустое, картинка НЕ пересобрана.")
        return False

    payload = json.dumps(epg, ensure_ascii=False)
    w, h, length = encode_text_to_png(payload, str(EPG_OUT))
    print(f"[epg] OK: {EPG_OUT.name} собран - {w}x{h} px, {length} байт")
    return True


if __name__ == "__main__":
    channels_only = len(sys.argv) > 1 and sys.argv[1] == "channels-only"

    ok = build_channels()
    if not channels_only:
        ok = build_epg() and ok

    sys.exit(0 if ok else 1)
