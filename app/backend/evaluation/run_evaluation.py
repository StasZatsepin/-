"""Оценка встроенных правил на синтетическом наборе с заложенными дефектами.

Запуск из app/backend (нужна база из .env, как для тестов и приложения):
    .venv\\Scripts\\python -m evaluation.run_evaluation

Важно: набор написан авторами, разметка задана при написании карточек.
Результат показывает, находят ли правила заложенные дефекты, и НЕ является
точностью на реальных карточках маркетплейсов.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.schemas.quick_check import QuickCheckRequest  # noqa: E402
from app.services.quick_check import run_quick_check  # noqa: E402

CLASSES = ["numeric", "ambiguous", "unconfirmed", "review"]
LABELS = {
    "numeric": "Числовое расхождение",
    "ambiguous": "Размытое обещание",
    "unconfirmed": "Утверждение без подтверждения",
    "review": "Расхождение с отзывами",
}


def rule_class(rule_id: str) -> str:
    if rule_id.startswith("numeric."):
        return "numeric"
    if rule_id == "claims.ambiguous_promise":
        return "ambiguous"
    if rule_id.startswith("evidence.missing"):
        return "unconfirmed"
    if rule_id == "reviews.numeric_mismatch":
        return "review"
    return ""


def main() -> None:
    data = json.loads((Path(__file__).with_name("synthetic_cards.json")).read_text(encoding="utf-8"))
    counts = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CLASSES}
    misses = []
    with SessionLocal() as db:
        for card in data["cards"]:
            request = QuickCheckRequest(
                name=card["id"],
                description=card["description"],
                attributes_text=card["attributes_text"],
                document_text=card["document_text"],
                reviews_text=card["reviews_text"],
            )
            result = run_quick_check(db, request)
            predicted = {rule_class(f.rule_id) for f in result.findings} - {""}
            expected = set(card["expected"])
            for cls in CLASSES:
                if cls in expected and cls in predicted:
                    counts[cls]["tp"] += 1
                elif cls in predicted:
                    counts[cls]["fp"] += 1
                    misses.append((card["id"], f"лишняя находка: {LABELS[cls]}"))
                elif cls in expected:
                    counts[cls]["fn"] += 1
                    misses.append((card["id"], f"пропущено: {LABELS[cls]}"))

    def ratio(a: int, b: int):
        return a / b if b else None

    def fmt(x):
        return "—" if x is None else f"{x:.2f}"

    lines = [
        f"# Результаты оценки на синтетическом наборе ({len(data['cards'])} карточек)",
        "",
        "Набор создан авторами; разметка задана при написании карточек. Это проверка того, находят ли правила "
        "заложенные дефекты, а не точность на реальных карточках маркетплейсов.",
        "",
        "| Класс | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    tp_all = fp_all = fn_all = 0
    for cls in CLASSES:
        tp, fp, fn = (counts[cls][k] for k in ("tp", "fp", "fn"))
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
        p, r = ratio(tp, tp + fp), ratio(tp, tp + fn)
        f1 = None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r)
        lines.append(f"| {LABELS[cls]} | {tp} | {fp} | {fn} | {fmt(p)} | {fmt(r)} | {fmt(f1)} |")
    p, r = ratio(tp_all, tp_all + fp_all), ratio(tp_all, tp_all + fn_all)
    f1 = None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r)
    lines.append(f"| **Все классы (микро)** | {tp_all} | {fp_all} | {fn_all} | {fmt(p)} | {fmt(r)} | {fmt(f1)} |")
    lines += ["", "## Ошибки", ""]
    lines += [f"- {cid}: {text}" for cid, text in misses] or ["- нет"]
    out = Path(__file__).with_name("results.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
