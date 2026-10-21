"""Скачивает шрифты Manrope и Inter локально (подмножества latin + cyrillic).

Скрипт выполняется один раз при подготовке проекта; в репозитории попадают
файлы public/fonts/*.woff2 и готовый styles/fonts.css, поэтому приложение
корректно работает без доступа в интернет.

Запуск: .venv\\Scripts\\python.exe scripts\\fetch_fonts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = PROJECT_ROOT / "app" / "frontend" / "public" / "fonts"
CSS_PATH = PROJECT_ROOT / "app" / "frontend" / "src" / "styles" / "fonts.css"

GOOGLE_CSS = (
    "https://fonts.googleapis.com/css2"
    "?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
KEEP_SUBSETS = {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}

BLOCK_RE = re.compile(
    r"(?P<comment>/\*\s*(?P<subset>[^*]+?)\s*\*/\s*)?"
    r"@font-face\s*\{(?P<body>[^}]+)\}",
    re.DOTALL,
)


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    CSS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=45.0, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(GOOGLE_CSS)
        response.raise_for_status()
        css = response.text

        blocks: list[tuple[str, str]] = []
        for match in BLOCK_RE.finditer(css):
            subset = (match.group("subset") or "").strip()
            if subset not in KEEP_SUBSETS:
                continue
            body = match.group("body")
            family = re.search(r"font-family:\s*'([^']+)'", body)
            weight = re.search(r"font-weight:\s*(\d+)", body)
            url = re.search(r"url\((https://[^)]+\.woff2)\)", body)
            if not (family and weight and url):
                continue
            blocks.append((family.group(1), weight.group(1), subset, url.group(1)))

        print(f"Найдено @font-face блоков: {len(blocks)}")
        rules: list[str] = []
        for family, weight, subset, url in blocks:
            filename = f"{family.lower()}-{weight}-{subset}.woff2"
            destination = TARGET_DIR / filename
            if not destination.exists():
                font = client.get(url)
                font.raise_for_status()
                destination.write_bytes(font.content)
                print(f"  скачан {filename} ({len(font.content) // 1024} КБ)")
            else:
                print(f"  уже есть {filename}")
            rules.append(
                "@font-face {\n"
                f"  font-family: '{family}';\n"
                "  font-style: normal;\n"
                f"  font-weight: {weight};\n"
                "  font-display: swap;\n"
                f"  src: url('/fonts/{filename}') format('woff2');\n"
                "}"
            )

    header = (
        "/* Шрифты Manrope и Inter (SIL Open Font License 1.1).\n"
        "   Подмножества latin, latin-ext, cyrillic, cyrillic-ext.\n"
        "   Файлы загружены локально — приложение работает без интернета. */\n\n"
    )
    CSS_PATH.write_text(header + "\n\n".join(rules) + "\n", encoding="utf-8")
    print(f"\nГотово: {len(rules)} правил записано в {CSS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
