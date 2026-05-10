#!/usr/bin/env python3
"""Render SVG charts and a markdown table from weekly.json into README.md.

The buckets chart shows the share of stories per editorial category per ISO week.
The words chart shows mean word count of the AI output vs. the published text.
The README is rewritten between the markers <!-- BEGIN:STATS --> ... <!-- END:STATS -->.
"""

import hashlib
import html
import json
from pathlib import Path

WEEKS_IN_TABLE = 12
WEEKS_IN_CHART = 16
BUCKETS_CHART_PATH = Path("chart-buckets.svg")
WORDS_CHART_PATH = Path("chart-words.svg")
README_PATH = Path("README.md")
DATA_PATH = Path("weekly.json")
BEGIN = "<!-- BEGIN:STATS -->"
END = "<!-- END:STATS -->"

WORDS_LINE_AI = "#2563eb"  # blue
WORDS_LINE_FINAL = "#0f172a"  # near-black

BUCKET_COLOURS = {
    "accurate": "#16a34a",  # green
    "edited": "#f59e0b",  # amber
    "rewritten": "#dc2626",  # red
}


def render_chart(weeks: list[dict]) -> str:
    width, height = 760, 360
    pad_l, pad_r, pad_t, pad_b = 60, 24, 60, 60
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    n = len(weeks)
    bar_gap = 6
    bar_w = (plot_w - bar_gap * (n - 1)) / n if n else 0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Share of accurate / edited / rewritten per week" '
        f'font-family="-apple-system, system-ui, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{pad_l}" y="22" font-weight="600" font-size="14" fill="#111">'
        f"Share of stories per editorial category, per week</text>",
    ]

    # Legend (top-left). Escape so the inline < and > stay as text, not XML markup.
    legend_items = [
        ("accurate", html.escape("accurate (<=5% changed)")),
        ("edited", html.escape("edited (5-40%)")),
        ("rewritten", html.escape("rewritten (>40%)")),
    ]
    lx = pad_l
    ly = 42
    for key, label in legend_items:
        parts.append(
            f'<rect x="{lx}" y="{ly - 9}" width="12" height="12" fill="{BUCKET_COLOURS[key]}"/>'
        )
        parts.append(f'<text x="{lx + 18}" y="{ly + 1}" fill="#374151">{label}</text>')
        lx += 8 * len(label) + 40

    # Y-axis grid + labels at 0, 25, 50, 75, 100
    for pct in (0, 25, 50, 75, 100):
        y = pad_t + plot_h * (1 - pct / 100)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#6b7280">{pct}%</text>'
        )

    # Stacked bars: accurate (bottom) -> edited -> rewritten (top)
    for i, w in enumerate(weeks):
        n_total = w["n"] or 1
        x = pad_l + i * (bar_w + bar_gap)
        cursor_y = pad_t + plot_h  # bottom up
        for key in ("accurate", "edited", "rewritten"):
            seg_h = plot_h * (w[key] / n_total)
            cursor_y -= seg_h
            parts.append(
                f'<rect x="{x:.1f}" y="{cursor_y:.1f}" '
                f'width="{bar_w:.1f}" height="{seg_h:.1f}" '
                f'fill="{BUCKET_COLOURS[key]}"/>'
            )
        # Week label + n=...
        label = w["week"].split("-", 1)[1]
        cx = x + bar_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 16}" '
            f'text-anchor="middle" fill="#374151">{label}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 32}" '
            f'text-anchor="middle" fill="#9ca3af" font-size="10">n={w["n"]}</text>'
        )

    # Axis line
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" '
        f'x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" stroke="#9ca3af"/>'
    )

    parts.append("</svg>\n")
    return "\n".join(parts)


def render_words_chart(weeks: list[dict]) -> str:
    width, height = 760, 320
    pad_l, pad_r, pad_t, pad_b = 60, 24, 60, 60
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    if not weeks:
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"></svg>\n'

    n = len(weeks)
    step = plot_w / max(n - 1, 1)

    max_words = max(max(w["words_ai_mean"], w["words_final_mean"]) for w in weeks)
    y_max = max(20, int((max_words + 19) // 20) * 20)

    def y_for(v: float) -> float:
        return pad_t + plot_h * (1 - v / y_max)

    def x_for(i: int) -> float:
        return pad_l + i * step

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Mean word count, AI vs. published, per week" '
        f'font-family="-apple-system, system-ui, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{pad_l}" y="22" font-weight="600" font-size="14" fill="#111">'
        f"Mean words per story (AI vs. published)</text>",
    ]

    legend = [(WORDS_LINE_AI, "AI"), (WORDS_LINE_FINAL, "published")]
    lx = pad_l
    for colour, label in legend:
        parts.append(
            f'<line x1="{lx}" y1="42" x2="{lx + 20}" y2="42" stroke="{colour}" stroke-width="2"/>'
        )
        parts.append(f'<circle cx="{lx + 10}" cy="42" r="3" fill="{colour}"/>')
        parts.append(f'<text x="{lx + 28}" y="46" fill="#374151">{label}</text>')
        lx += 28 + 8 * len(label) + 30

    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        v = y_max * frac
        y = y_for(v)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" stroke="#e5e7eb"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#6b7280">'
            f"{int(v)}</text>"
        )

    for i, w in enumerate(weeks):
        cx = x_for(i)
        label = w["week"].split("-", 1)[1]
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 16}" '
            f'text-anchor="middle" fill="#374151">{label}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 32}" '
            f'text-anchor="middle" fill="#9ca3af" font-size="10">n={w["n"]}</text>'
        )

    for key, colour in (("words_ai_mean", WORDS_LINE_AI), ("words_final_mean", WORDS_LINE_FINAL)):
        points = " ".join(f"{x_for(i):.1f},{y_for(w[key]):.1f}" for i, w in enumerate(weeks))
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2"/>'
        )
        for i, w in enumerate(weeks):
            parts.append(
                f'<circle cx="{x_for(i):.1f}" cy="{y_for(w[key]):.1f}" r="3" fill="{colour}"/>'
            )

    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" '
        f'x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" stroke="#9ca3af"/>'
    )
    parts.append("</svg>\n")
    return "\n".join(parts)


def render_table(weeks: list[dict]) -> str:
    header = (
        "| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    )
    rows = []
    for w in weeks:
        n = w["n"] or 1
        rows.append(
            f"| {w['week']} | {w['n']} | "
            f"{w['accurate'] / n * 100:.0f}% | "
            f"{w['edited'] / n * 100:.0f}% | "
            f"{w['rewritten'] / n * 100:.0f}% | "
            f"{w['words_ai_mean']:.0f} | "
            f"{w['words_final_mean']:.0f} |"
        )
    return header + "\n".join(rows) + "\n"


def cache_bust(path: Path) -> str:
    """Short content hash so GitHub's image cache refreshes when the SVG changes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def render_section(weeks: list[dict]) -> str:
    if not weeks:
        return f"{BEGIN}\n_No data yet._\n{END}\n"
    table_weeks = weeks[-WEEKS_IN_TABLE:][::-1]  # newest first
    last = weeks[-1]
    n = last["n"] or 1
    headline = (
        f"**Last week ({last['week']}, n={last['n']}):**\n\n"
        f"- {last['accurate'] / n * 100:.0f}% accurate\n"
        f"- {last['edited'] / n * 100:.0f}% edited\n"
        f"- {last['rewritten'] / n * 100:.0f}% rewritten"
    )
    buckets_url = f"{BUCKETS_CHART_PATH.name}?v={cache_bust(BUCKETS_CHART_PATH)}"
    words_url = f"{WORDS_CHART_PATH.name}?v={cache_bust(WORDS_CHART_PATH)}"
    return (
        f"{BEGIN}\n"
        f"## Latest results\n\n"
        f"{headline}\n\n"
        f"![Share of accurate / edited / rewritten per week]({buckets_url})\n\n"
        f"![Mean word count AI vs. published per week]({words_url})\n\n"
        f"{render_table(table_weeks).rstrip()}\n"
        f"{END}"
    )


def splice(readme: str, section: str) -> str:
    """Replace the BEGIN..END block with section, normalising surrounding blank lines."""
    if BEGIN in readme and END in readme:
        before = readme.split(BEGIN, 1)[0].rstrip("\n")
        after = readme.split(END, 1)[1].lstrip("\n")
        return f"{before}\n\n{section}\n\n{after}"
    # First run: insert before the "## Running locally" header, else at end.
    anchor = "\n## Running locally"
    if anchor in readme:
        before, rest = readme.split(anchor, 1)
        return f"{before.rstrip()}\n\n{section}\n{anchor}{rest}"
    return f"{readme.rstrip()}\n\n{section}\n"


def main() -> None:
    weeks = json.loads(DATA_PATH.read_text())
    weeks.sort(key=lambda w: w["week"])

    chart_weeks = weeks[-WEEKS_IN_CHART:]
    BUCKETS_CHART_PATH.write_text(render_chart(chart_weeks))
    WORDS_CHART_PATH.write_text(render_words_chart(chart_weeks))
    README_PATH.write_text(splice(README_PATH.read_text(), render_section(weeks)))


if __name__ == "__main__":
    main()
