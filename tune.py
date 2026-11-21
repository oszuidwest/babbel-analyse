#!/usr/bin/env python3
"""Learn from the editors' edits and test a better speech prompt.

Proposes a new prompt from the edited stories of the last 35 days and tests it against
speech-prompt.txt on the newest 40 stories. Writes a report to reports/ and prints
report=... and accepted=... for the workflow. When the new prompt is clearly better, it
also overwrites speech-prompt.txt.
"""

import datetime as dt
import difflib
import json
import math
import os
import random
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import label

PROMPT = Path("speech-prompt.txt")
PROD_MODEL = os.environ.get("PROD_MODEL", "gpt-5.6-sol")  # keep equal to the plugin setting
DAYS, TEST, LEARN, MIN_LEARN = 35, 40, 60, 30
WORD_LIMIT = 70  # soft: the editors publish over 65 words in about 40% of the stories
# Longer stories and proposed prompts are skipped, not cut, so the test sees the real
# input; with at most 121 calls these limits bound what a run sends.
ARTICLE_MAX, TEXT_MAX, PROMPT_MAX = 8000, 1500, 4000

# Mirrors includes/ai-handler.php in zw-knabbel-wp.
ARTICLE = 'Artikel:\n"""\n{}\n"""'
EXAMPLE = (
    "{} — leer van toon, nieuwsselectie en formulering. Neem geen feiten over. "
    "De lengte en het zinsaantal kunnen afwijken van de instructie voor het nieuwe artikel."
)
ACCEPTED = "VOORBEELD DAT DE REDACTIE DIRECT HEEFT GEACCEPTEERD"
EDITED = "VOORBEELD DAT DE REDACTIE HEEFT AANGEPAST"

PROPOSE = (
    "You maintain the system prompt of a model that writes Dutch radio news texts from "
    "articles. You get the current prompt and pairs of AI text and the text the editors "
    "broadcast. Find changes that recur and that a prompt can teach; ignore fact fixes, news "
    "added later, timing and one-off taste. Change the prompt as little as needed, in Dutch, "
    "without examples from specific articles, and leave it unchanged when nothing recurs. "
    "Keep these rules: every statement is supported by the article and nothing is added; "
    "names, places, dates, times and numbers stay as they are; one paragraph of at most 65 "
    "words; spoken Dutch at B1 level; keep or add the {year} placeholder for the current year."
)
JUDGE = (
    "You compare two Dutch radio news texts, A and B, written from the same article. Check "
    "each against the article: does it state anything the article does not support, such as "
    "changed names, places, dates or numbers, or a plan told as a fact? Then decide which one "
    "an editor would need to change less to get a text they would broadcast like the "
    "reference. Do not reward sharing exact words with the reference."
)


def with_year(prompt, when):
    """{year} as the plugin fills it: wp_date('Y'), in the site's timezone."""
    year = dt.datetime.fromisoformat(when).astimezone(ZoneInfo("Europe/Amsterdam")).year
    return prompt.replace("{year}", str(year))


def cases(stories, prompt):
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    out = []
    for s in stories:
        md = s.get("metadata") or {}
        gen = md.get("generation") or {}
        c = {
            "created_at": s["created_at"],
            "ai": md.get("original_speech_text"),
            "final": s.get("text"),
        }
        c |= {"article": gen.get("article"), "generated_at": gen.get("generated_at")}
        if (
            s["created_at"] >= since
            and s.get("status") == "expired"
            and not s.get("deleted_at")
            and c["ai"]
            and c["final"]
            and c["article"]
            and len(c["article"]) <= ARTICLE_MAX
            and max(len(c["ai"]), len(c["final"])) <= TEXT_MAX
            and gen.get("prompt") == with_year(prompt, gen["generated_at"])
        ):
            out.append(c)
    return sorted(out, key=lambda c: c["created_at"])


def generate(prompt, examples, c):
    """One text, requested like the plugin does."""
    msgs = []
    for lab, e in examples:
        user = EXAMPLE.format(lab) + "\n\n" + ARTICLE.format(" ".join(e["article"].split()))
        msgs += [{"role": "user", "content": user}, {"role": "assistant", "content": e["final"]}]
    msgs.append({"role": "user", "content": ARTICLE.format(c["article"])})
    instructions = with_year(prompt, c["generated_at"])  # the year the plugin filled in
    return label.call(instructions, msgs, model=PROD_MODEL, json_mode=False, max_tokens=1000)


def judge(c, current, new, swap):
    a, b = (new, current) if swap else (current, new)
    out = label.call(
        JUDGE,
        f"ARTICLE:\n{c['article']}\n\nREFERENCE:\n{c['final']}\n\nA:\n{a}\n\nB:\n{b}\n\n"
        'Answer in JSON: {"better": "A", "B" or "same", "a_unsupported": true or false, '
        '"b_unsupported": true or false}',
    )
    r = json.loads(out)
    if r.get("better") not in ("A", "B", "same") or not all(
        isinstance(r.get(k), bool) for k in ("a_unsupported", "b_unsupported")
    ):
        raise ValueError(f"malformed judgement: {out}")  # stop rather than guess
    names = {"A": "new" if swap else "current", "B": "current" if swap else "new"}
    unsupported = {names["A"]: r["a_unsupported"], names["B"]: r["b_unsupported"]}
    return names.get(r["better"], "same"), unsupported


def check(prompt, cs):
    """The report lines and the new prompt, or None when it does not win."""
    test, rest = cs[-TEST:], cs[:-TEST]
    lines = [
        f"{len(cs)} stories made with the current prompt; the newest {len(test)} are the test."
    ]
    if len(test) < TEST or len(rest) < MIN_LEARN:
        return lines + ["", "No change: too few stories."], None
    edited = [c for c in reversed(rest) if label.edit_fraction(c["ai"], c["final"]) > 0]
    examples = [(ACCEPTED, c) for c in reversed(rest) if c["ai"] == c["final"]][:3]
    examples += [(EDITED, c) for c in edited[:5]]
    pairs = "\n\n".join(f"AI: {c['ai']}\nBROADCAST: {c['final']}" for c in edited[:LEARN])
    out = label.call(
        PROPOSE,
        f"CURRENT PROMPT:\n<<<\n{prompt}\n>>>\n\n{pairs}\n\n"
        'Answer in JSON: {"prompt": "...", "changes": ["..."]}',
    )
    proposal = json.loads(out)
    new = proposal["prompt"]
    if new.strip() == prompt.strip():
        return lines + ["", "No change: nothing recurring to act on."], None
    if len(new) > PROMPT_MAX:
        return lines + ["", f"No change: the proposal is over {PROMPT_MAX} characters."], None

    count = {"new": 0, "current": 0, "same": 0}
    unsupported = {"new": 0, "current": 0}
    over = {"new": 0, "current": 0}
    rng = random.Random(0)
    for c in test:
        texts = {"current": generate(prompt, examples, c), "new": generate(new, examples, c)}
        if not all(texts.values()):
            return lines + ["", "No change: a text could not be generated."], None
        better, unsup = judge(c, texts["current"], texts["new"], rng.random() < 0.5)
        count[better] += 1
        for k in texts:
            unsupported[k] += unsup[k]
            over[k] += len(texts[k].split()) > WORD_LIMIT
    n = count["new"] + count["current"]
    p = sum(math.comb(n, k) for k in range(count["new"], n + 1)) / 2**n if n else 1.0
    wins = count["new"] > count["current"] and p < 0.05
    ok = wins and unsupported["new"] <= unsupported["current"] and over["new"] <= over["current"]
    lines += [
        "",
        f"{'New prompt proposed' if ok else 'No change'}: it needs to win the blind comparison "
        "(p < 0.05) without more unsupported statements or texts over 70 words.",
        "",
        "| | Current | New |",
        "| --- | ---: | ---: |",
        f"| Better in the blind comparison | {count['current']} | {count['new']} |",
        f"| Text with an unsupported statement | {unsupported['current']} | {unsupported['new']} |",
        f"| Text over {WORD_LIMIT} words | {over['current']} | {over['new']} |",
        "",
        f"Same: {count['same']}. Chance the new prompt wins this often by luck: p = {p:.3f}.",
        "",
        "## Changes",
        "",
        *[f"- {ch}" for ch in proposal.get("changes", [])],
        "",
        "## Prompt diff",
        "",
        "```diff",
        *difflib.unified_diff(prompt.splitlines(), new.splitlines(), "current", "new", lineterm=""),
        "```",
    ]
    return lines, new if ok else None


def main():
    prompt = PROMPT.read_bytes().decode()  # keep the CRLF line ends the live prompt has
    cs = cases(json.loads(Path("stories.json").read_text()), prompt)
    lines, new = check(prompt, cs)
    report = Path("reports") / f"{dt.date.today().isoformat()}.md"
    report.parent.mkdir(exist_ok=True)
    text = "\n".join([f"# Prompt check {dt.date.today().isoformat()}", "", *lines, ""])
    report.write_text(text)
    print(text, file=sys.stderr)  # also in the job log, in case pushing the report fails
    if new:
        PROMPT.write_text(new)
    print(f"report={report}\naccepted={'true' if new else 'false'}")


if __name__ == "__main__":
    main()
