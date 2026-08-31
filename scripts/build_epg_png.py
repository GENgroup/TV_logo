"""
Пересобирает epg-data.png из свежей выгрузки programtv.ru.
Запускается роботом (GitHub Actions) каждую ночь.

Если источник (programtv.ru) недоступен или отдал что-то нечитаемое -
скрипт останавливается с понятной ошибкой и СТАРАЯ картинка остаётся
нетронутой - зрители не останутся совсем без EPG из-за разового сбоя
источника, просто останется вчерашнее расписание ещё на сутки.
"""
import gzip
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from encode_to_png import encode_text_to_png

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "epg-data.png"

# личная ссылка пользователя на programtv.ru (см. GEN-tv-handoff) -
# если понадобится сменить/пересоздать выгрузку на сайте - поменять
# только этот адрес, больше ничего трогать не нужно
EPG_SOURCE_URL = "http://programtv.ru/xmltv.xml.gz/491676941"

CHANNEL_RE = re.compile(
    r'<channel id="(\d+)">\s*<display-name>(.*?)</display-name>', re.S
)
PROG_RE = re.compile(
    r'<programme start="([^"]+)" stop="([^"]+)" channel="(\d+)">\s*'
    r'<title>(.*?)</title>', re.S
)


def unescape(s: str) -> str:
    return (s.replace("&quot;", '"').replace("&amp;", "&")
             .replace("&#039;", "'").replace("&lt;", "<").replace("&gt;", ">"))


def main():
    print(f"Качаю: {EPG_SOURCE_URL}")

    raw = None
    last_error = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(EPG_SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                expected = resp.headers.get("Content-Length")
                if expected is not None and int(expected) != len(raw):
                    raise IOError(
                        f"скачано {len(raw)} байт, а сервер обещал {expected} - обрыв"
                    )
            # сразу пробуем распаковать - если файл битый, узнаем здесь же и повторим попытку
            gzip.decompress(raw)
            break
        except Exception as e:
            last_error = e
            print(f"Попытка {attempt}/3 не удалась: {e}")
            raw = None
            time.sleep(5)

    if raw is None:
        print(f"ОШИБКА: не удалось скачать источник EPG за 3 попытки - {last_error}")
        sys.exit(1)

    text = gzip.decompress(raw).decode("utf-8")

    channels = dict(CHANNEL_RE.findall(text))
    print(f"Каналов в источнике: {len(channels)}")

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
    print(f"Каналов с расписанием: {len(epg)}, передач: {total} (повторов убрано: {dup_count})")

    if not epg:
        print("ОШИБКА: расписание получилось пустым, картинка НЕ пересобрана.")
        sys.exit(1)

    payload = json.dumps(epg, ensure_ascii=False)
    width, length = encode_text_to_png(payload, str(OUT))
    print(f"OK: {OUT.name} собран - {width}x1 px, {length} байт данных")


if __name__ == "__main__":
    main()
