#!/usr/bin/env python3
"""Per-week comparison of AI output (metadata.original_speech_text) vs final text."""

import datetime as dt
import difflib
import json
import statistics
from collections import defaultdict

# Bucket thresholds, by token-edit fraction (Levenshtein over word tokens).
ACCURATE_MAX = 0.05  # <=5% of words changed
EDITED_MAX = 0.40  # 5-40% of words changed; rewritten = the remainder

with open("stories.json") as f:
    stories = json.load(f)


def norm(s: str) -> str:
    return " ".join((s or "").split())


def tokens(s: str) -> list[str]:
    return norm(s).split()


def char_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def token_edit_fraction(a: list[str], b: list[str]) -> float:
    """Fraction of tokens changed when going AI -> final.
    1 - (matched_tokens / max(len_ai, len_final))."""
    if not a and not b:
        return 0.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    matched = sum(t.size for t in sm.get_matching_blocks())
    denom = max(len(a), len(b)) or 1
    return 1 - matched / denom


# Filter to stories with both AI text and final text
usable = []
for s in stories:
    md = s.get("metadata") or {}
    ai = md.get("original_speech_text")
    final = s.get("text")
    if not ai or not final:
        continue
    usable.append(
        {
            "id": s["id"],
            "created_at": s["created_at"],
            "ai": ai,
            "final": final,
        }
    )

print(f"total stories: {len(stories)}")
print(f"usable (both AI + final present): {len(usable)}")
print(f"discarded: {len(stories) - len(usable)}\n")

# Bucket by ISO week
weekly = defaultdict(list)
for s in usable:
    d = dt.datetime.fromisoformat(s["created_at"])
    iso_year, iso_week, _ = d.isocalendar()
    key = f"{iso_year}-W{iso_week:02d}"
    s["char_sim"] = char_similarity(norm(s["ai"]), norm(s["final"]))
    s["tok_edit"] = token_edit_fraction(tokens(s["ai"]), tokens(s["final"]))
    s["len_ratio"] = len(norm(s["final"])) / max(len(norm(s["ai"])), 1)
    s["unchanged"] = norm(s["ai"]) == norm(s["final"])
    weekly[key].append(s)


def med(xs):
    return statistics.median(xs) if xs else 0.0


def mean(xs):
    return statistics.fmean(xs) if xs else 0.0


print(
    f"{'week':<10} {'n':>4}  {'%unchg':>7}  {'sim_med':>8}  {'sim_mean':>8}  "
    f"{'tokedit_med':>11}  {'tokedit_mean':>12}  {'len_ratio_med':>13}"
)
print("-" * 95)

rows = []
for week in sorted(weekly):
    items = weekly[week]
    n = len(items)
    pct_unchg = sum(1 for x in items if x["unchanged"]) / n * 100
    sims = [x["char_sim"] for x in items]
    toks = [x["tok_edit"] for x in items]
    lens = [x["len_ratio"] for x in items]
    words_ai = [len(tokens(x["ai"])) for x in items]
    words_final = [len(tokens(x["final"])) for x in items]
    accurate = sum(1 for x in items if x["tok_edit"] <= ACCURATE_MAX)
    edited = sum(1 for x in items if ACCURATE_MAX < x["tok_edit"] <= EDITED_MAX)
    rewritten = n - accurate - edited
    rows.append(
        {
            "week": week,
            "n": n,
            "pct_unchg": pct_unchg,
            "sim_med": med(sims),
            "sim_mean": mean(sims),
            "tok_med": med(toks),
            "tok_mean": mean(toks),
            "len_med": med(lens),
            "accurate": accurate,
            "edited": edited,
            "rewritten": rewritten,
            "words_ai_mean": mean(words_ai),
            "words_final_mean": mean(words_final),
        }
    )
    print(
        f"{week:<10} {n:>4}  {pct_unchg:>6.1f}%  {med(sims):>8.3f}  {mean(sims):>8.3f}  "
        f"{med(toks):>11.3f}  {mean(toks):>12.3f}  {med(lens):>13.3f}"
    )

# Save for further analysis
with open("weekly.json", "w") as f:
    json.dump(rows, f, indent=2)

# First half vs second half (by chronology of weeks present)
weeks_sorted = sorted(weekly)
half = len(weeks_sorted) // 2
first_half = [w for ws in weeks_sorted[:half] for w in weekly[ws]]
second_half = [w for ws in weeks_sorted[half:] for w in weekly[ws]]

print(
    f"\n=== first half ({weeks_sorted[0]}..{weeks_sorted[half - 1]}, "
    f"n={len(first_half)}) vs second half "
    f"({weeks_sorted[half]}..{weeks_sorted[-1]}, n={len(second_half)}) ==="
)


def block(name, items):
    sims = [x["char_sim"] for x in items]
    toks = [x["tok_edit"] for x in items]
    lens = [x["len_ratio"] for x in items]
    pct = sum(1 for x in items if x["unchanged"]) / len(items) * 100
    print(
        f"{name:<12} %unchg={pct:5.1f}  sim_med={med(sims):.3f}  "
        f"sim_mean={mean(sims):.3f}  tokedit_med={med(toks):.3f}  "
        f"tokedit_mean={mean(toks):.3f}  len_ratio_med={med(lens):.3f}"
    )


block("first half", first_half)
block("second half", second_half)

# Worst/best examples in latest 4 weeks
recent = [x for ws in weeks_sorted[-4:] for x in weekly[ws]]
recent.sort(key=lambda x: x["tok_edit"], reverse=True)
print("\n=== worst 5 token-edits in last 4 weeks ===")
for x in recent[:5]:
    print(f"  id={x['id']} tok_edit={x['tok_edit']:.3f} sim={x['char_sim']:.3f}")
    print(f"    AI : {x['ai'][:150]}")
    print(f"    fin: {x['final'][:150]}")
