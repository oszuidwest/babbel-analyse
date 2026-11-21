#!/usr/bin/env python3
"""Label which kinds of change the editors made to edited AI texts, into labels.json.

--sample N labels N random stories and writes pilot.json for the label check page.
"""

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import random
import urllib.request
from pathlib import Path

MAX_CALLS = int(os.environ.get("MAX_CALLS", "5"))  # each call is capped, so this caps the cost
ARTICLE_CHARS = 8000
OUTPUT_TOKENS = 8000
VERSION = 1  # bump when the instructions or kinds change, to relabel on purpose
KINDS = {
    "fact": "the AI text said something the article does not support, and the editors fixed it",
    "missing": "the AI text left out something from the article that the editors added",
    "extra": "the editors added information that is not in the article",
    "timing": "the edit is about when the text airs (tense, 'vandaag' vs a weekday, ...)",
    "style": "a general writing rule the AI could follow next time",
    "taste": "a change without a clear general rule",
}
INSTRUCTIONS = (
    "For each item you get a news article, the Dutch radio text an AI wrote from it, and the "
    "text the editors broadcast. Say which kinds of change the editors made; use every kind "
    "that applies, and only those:\n" + "\n".join(f"- {k}: {v}" for k, v in KINDS.items())
)
calls = 0


def classify(model, batch):
    """Kinds per story id for one batch of at most BATCH stories."""
    global calls
    if calls >= MAX_CALLS:
        raise RuntimeError(f"MAX_CALLS ({MAX_CALLS}) reached")
    calls += 1
    text = 'Answer in JSON: {"items": [{"id": "...", "kinds": ["..."]}]}\n\n' + "\n\n".join(
        f"ITEM {c['id']}\nARTICLE: {c['article'][:ARTICLE_CHARS]}\nAI: {c['ai']}\n"
        f"BROADCAST: {c['final']}"
        for c in batch
    )
    body = {
        "model": model,
        "instructions": INSTRUCTIONS,
        "input": text,
        "max_output_tokens": OUTPUT_TOKENS,
        "text": {"format": {"type": "json_object"}},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    if res.get("status") != "completed":
        return {}
    out = "".join(
        c.get("text", "") for o in res["output"] if o["type"] == "message" for c in o["content"]
    )
    ids = {c["id"] for c in batch}
    return {
        str(i["id"]): sorted({k for k in i["kinds"] if k in KINDS})
        for i in json.loads(out)["items"]
        if str(i["id"]) in ids
    }


def texts_hash(ai: str, final: str) -> str:
    return hashlib.sha256(f"{ai}\0{final}".encode()).hexdigest()


LABELS = Path("labels.json")
BATCH = 12


def edit_fraction(a: str, b: str) -> float:
    ta, tb = a.split(), b.split()
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    return 1 - sum(m.size for m in sm.get_matching_blocks()) / max(len(ta), len(tb), 1)


def cases(stories, articles, since):
    for s in stories:
        md = s.get("metadata") or {}
        ai, final = md.get("original_speech_text"), s.get("text")
        gen = md.get("generation") or {}
        article = gen.get("article") or articles.get(str(s["id"]))
        if (
            s["created_at"] >= since
            and s.get("status") == "expired"
            and not s.get("deleted_at")
            and ai
            and final
            and article
            and edit_fraction(ai, final) > 0.05
        ):
            yield {
                "id": str(s["id"]),
                "date": s["created_at"][:10],
                "ai": ai,
                "final": final,
                "article": article,
            }


def is_current(label, c):
    return (
        label is not None
        and label.get("version") == VERSION
        and label.get("texts") == texts_hash(c["ai"], c["final"])
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stories", type=Path, default=Path("stories.json"))
    ap.add_argument("--articles", type=Path)
    ap.add_argument("--model", default=os.environ.get("LABEL_MODEL", "gpt-6.2-sol"))
    ap.add_argument("--sample", type=int)
    args = ap.parse_args()

    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=92)).strftime("%Y-%m-%dT%H:%M:%S")
    articles = json.loads(args.articles.read_text()) if args.articles else {}
    labels = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    todo = list(cases(json.loads(args.stories.read_text()), articles, since))
    if args.sample:
        todo = random.Random(0).sample(todo, min(args.sample, len(todo)))
    pending = [c for c in todo if not is_current(labels.get(c["id"]), c)]
    print(f"{len(todo)} stories, {len(pending)} to label")

    try:
        for i in range(0, len(pending), BATCH):
            batch = pending[i : i + BATCH]
            for sid, kinds in classify(args.model, batch).items():
                c = next(c for c in batch if c["id"] == sid)
                labels[sid] = {
                    "kinds": kinds,
                    "version": VERSION,
                    "texts": texts_hash(c["ai"], c["final"]),
                }
            # Save after every call, so a stopped run keeps what it paid for.
            LABELS.write_text(json.dumps(labels, ensure_ascii=False, indent=1, sort_keys=True))
    finally:
        print(f"{calls} calls made")

    if args.sample:
        pilot = [
            c | {"kinds": labels[c["id"]]["kinds"]}
            for c in sorted(todo, key=lambda c: c["date"])
            if is_current(labels.get(c["id"]), c)
        ]
        Path("pilot.json").write_text(json.dumps(pilot, ensure_ascii=False))


if __name__ == "__main__":
    main()
