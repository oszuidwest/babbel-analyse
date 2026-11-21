#!/usr/bin/env python3
"""Label which kinds of change the editors made to edited AI texts, into labels.json.

Old stories need their article from --articles ({story_id: article}); new ones carry it.
"""

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import urllib.request
from pathlib import Path

MODEL = "gpt-6.2-sol"
MAX_CALLS = int(os.environ.get("MAX_CALLS", "5"))
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


def call(instructions, text, model=MODEL, json_mode=True, max_tokens=OUTPUT_TOKENS):
    """One OpenAI Responses call; the answer text, or None when it did not complete."""
    global calls
    if calls >= MAX_CALLS:
        raise RuntimeError(f"MAX_CALLS ({MAX_CALLS}) reached")
    calls += 1
    body = {"model": model, "instructions": instructions, "input": text}
    body["max_output_tokens"] = max_tokens
    if json_mode:
        body["text"] = {"format": {"type": "json_object"}}
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
        return None
    return "".join(
        c.get("text", "") for o in res["output"] if o["type"] == "message" for c in o["content"]
    )


def classify(batch):
    """The model's answer items for one batch of stories."""
    text = 'Answer in JSON: {"items": [{"id": "...", "kinds": ["..."]}]}\n\n' + "\n\n".join(
        f"ITEM {c['id']}\nARTICLE: {c['article'][:ARTICLE_CHARS]}\nAI: {c['ai']}\n"
        f"BROADCAST: {c['final']}"
        for c in batch
    )
    out = call(INSTRUCTIONS, text)
    return json.loads(out)["items"] if out else []


def key(c) -> str:
    """A label counts only for this classifier version and these exact texts."""
    return hashlib.sha256(f"{VERSION}\0{c['ai']}\0{c['final']}".encode()).hexdigest()


LABELS = Path("labels.json")
BATCH = 12


def edit_fraction(a: str, b: str) -> float:
    """Share of words changed from a to b; the weekly table uses it too."""
    ta, tb = a.split(), b.split()
    if not ta and not tb:
        return 0.0
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    n = max(len(ta), len(tb))
    return (n - sum(m.size for m in sm.get_matching_blocks())) / n  # exact at 5%, no 1 - x


def is_current(label, c):
    return label is not None and label.get("key") == key(c)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--articles", type=Path)
    args = ap.parse_args()
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=92)).strftime("%Y-%m-%dT%H:%M:%S")
    articles = json.loads(args.articles.read_text()) if args.articles else {}
    labels = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    pending = []
    for s in json.loads(Path("stories.json").read_text()):
        md = s.get("metadata") or {}
        c = {
            "id": str(s["id"]),
            "ai": md.get("original_speech_text") or "",
            "final": s.get("text") or "",
            "article": (md.get("generation") or {}).get("article") or articles.get(str(s["id"])),
        }
        if (
            s["created_at"] >= since
            and s.get("status") == "expired"
            and not s.get("deleted_at")
            and c["ai"]
            and c["final"]
            and c["article"]
            and edit_fraction(c["ai"], c["final"]) > 0.05
            and not is_current(labels.get(c["id"]), c)
        ):
            pending.append(c)
    print(f"{len(pending)} stories to label")
    # At most MAX_CALLS calls, each with a capped article and answer; the rest waits.
    for i in range(0, min(len(pending), MAX_CALLS * BATCH), BATCH):
        batch = {c["id"]: c for c in pending[i : i + BATCH]}
        for item in classify(batch.values()):
            if not isinstance(item, dict) or not isinstance(item.get("kinds"), list):
                continue  # a malformed item must not cost the valid ones
            sid = str(item.get("id"))
            kinds = sorted({k for k in item["kinds"] if isinstance(k, str) and k in KINDS})
            if sid in batch and kinds:  # unknown ids and empty answers are skipped
                labels[sid] = {"kinds": kinds, "key": key(batch[sid])}
        # Save after every call, so a stopped run keeps what it paid for.
        LABELS.write_text(json.dumps(labels, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
