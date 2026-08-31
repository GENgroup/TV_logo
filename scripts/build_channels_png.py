"""
Пересобирает channels-data.png из channels-list.json.
Запускается роботом (GitHub Actions) при изменении channels-list.json,
а также каждую ночь вместе с EPG.

Если в channels-list.json синтаксическая ошибка (как в старой истории
с пропущенной скобкой) - скрипт остановится с понятной ошибкой и
СТАРАЯ картинка останется нетронутой (ничего не сломает у пользователя).
"""
import json
import sys
from pathlib import Path
from encode_to_png import encode_text_to_png

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "channels-list.json"
OUT = ROOT / "channels-data.png"


def main():
    if not SRC.exists():
        print(f"ОШИБКА: не найден {SRC}")
        sys.exit(1)

    text = SRC.read_text(encoding="utf-8")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ОШИБКА: {SRC.name} - невалидный JSON, картинка НЕ пересобрана.")
        print(f"Подробности: {e}")
        sys.exit(1)

    groups = data.get("groups", [])
    total_items = sum(len(g.get("items", [])) for g in groups)
    print(f"Групп: {len(groups)}, каналов всего: {total_items}")

    width, length = encode_text_to_png(text, str(OUT))
    print(f"OK: {OUT.name} собран - {width}x1 px, {length} байт данных")


if __name__ == "__main__":
    main()
