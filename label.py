#!/usr/bin/env python3
"""Label what kind of changes the editors made to edited AI texts.

Reads stories.json (from fetch_all.py) and keeps labels.json up to date: one entry per
finished story where the editors changed more than 5% of the words. A story is labelled
once; it is labelled again only when its texts change or the classifier version changes.

The classifier needs the article the AI worked from. New stories carry it in
metadata.generation (recorded by the plugin). For older stories, --articles takes a JSON
file {story_id: article} rebuilt from WordPress revisions. Stories without an article are
not labelled and count as not covered.

--sample N labels a random sample and writes pilot.md, so an editor can check the labels
before they are published in the README.
"""

import argparse
import difflib
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import llm

LABELS_PATH = Path("labels.json")
EDITED_MIN = 0.05  # same threshold as analyze.py's "accurate" bucket


def norm(s: str) -> str:
    return " ".join((s or "").split())


def token_edit(a: str, b: str) -> float:
    ta, tb = norm(a).split(), norm(b).split()
    if not ta and not tb:
        return 0.0
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    return 1 - sum(m.size for m in sm.get_matching_blocks()) / max(len(ta), len(tb))


def word_diff(a: str, b: str) -> str:
    ta, tb = norm(a).split(), norm(b).split()
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    return " ".join(
        f"[{' '.join(ta[i1:i2])} -> {' '.join(tb[j1:j2])}]"
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
        if tag != "equal"
    )


def input_hash(c) -> str:
    return hashlib.sha256(f"{c['article']}\0{c['ai']}\0{c['final']}".encode()).hexdigest()


def edited_cases(stories, articles):
    """Finished, edited stories with the article the AI worked from."""
    cases, no_article = [], 0
    for s in stories:
        md = s.get("metadata") or {}
        ai, final = md.get("original_speech_text"), s.get("text")
        if s.get("deleted_at") or s.get("status") != "expired" or not ai or not final:
            continue
        if token_edit(ai, final) <= EDITED_MIN:
            continue
        gen = md.get("generation") if isinstance(md.get("generation"), dict) else {}
        article, source = gen.get("article"), "recorded"
        if not article:
            article, source = articles.get(str(s["id"])), "revision"
        if not article:
            no_article += 1
            continue
        cases.append(
            {
                "id": str(s["id"]),
                "created_at": s["created_at"],
                "article": norm(article),
                "source": source,
                "ai": norm(ai),
                "final": norm(final),
            }
        )
    return cases, no_article


def write_pilot(path, cases, labels):
    lines = [
        "# Label check",
        "",
        "For each story, check the labels the model gave. Write next to each label whether "
        "it is right, and add any kind it missed.",
        "",
        "Kinds: " + "; ".join(f"{k}: {v}" for k, v in llm.KINDS.items()) + ".",
        "",
    ]
    for c in cases:
        lab = labels.get(c["id"], {})
        lines += [
            f"## Story {c['id']} ({c['created_at'][:10]})",
            "",
            f"Labels: {', '.join(lab.get('kinds', [])) or '(none)'}",
            "",
            f"AI: {c['ai']}",
            "",
            f"Published: {c['final']}",
            "",
            f"Changes: {word_diff(c['ai'], c['final'])}",
            "",
            "<details><summary>Article</summary>",
            "",
            c["article"],
            "",
            "</details>",
            "",
        ]
    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stories", type=Path, default=Path("stories.json"))
    ap.add_argument("--articles", type=Path, help="JSON {story_id: article} for old stories")
    ap.add_argument("--model", default=os.environ.get("LABEL_MODEL", "gpt-5.6-sol"))
    ap.add_argument("--sample", type=int, help="label a random sample and write pilot.md")
    args = ap.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY must be set")
    model = args.model.removeprefix("openai/")

    stories = json.loads(args.stories.read_text())
    articles = json.loads(args.articles.read_text()) if args.articles else {}
    labels = json.loads(LABELS_PATH.read_text()) if LABELS_PATH.exists() else {}
    cases, no_article = edited_cases(stories, articles)

    todo = [
        c
        for c in cases
        if labels.get(c["id"], {}).get("input") != input_hash(c)
        or labels[c["id"]].get("version") != llm.CLASSIFIER_VERSION
    ]
    if args.sample:
        todo = random.Random(0).sample(cases, min(args.sample, len(cases)))
    print(
        f"{len(cases)} edited stories with an article ({no_article} without), {len(todo)} to label",
        file=sys.stderr,
    )

    done = []
    try:
        for i in range(0, len(todo), 120):
            chunk = todo[i : i + 120]
            for item in llm.classify(model, chunk, word_diff):
                c = next(c for c in chunk if c["id"] == item["id"])
                labels[c["id"]] = {
                    "kinds": sorted(set(item["kinds"])),
                    "rules": item["rules"],
                    "source": c["source"],
                    "model": model,
                    "version": llm.CLASSIFIER_VERSION,
                    "input": input_hash(c),
                }
                done.append(c["id"])
            # Save after each chunk, so a stopped run keeps what it paid for.
            LABELS_PATH.write_text(json.dumps(labels, ensure_ascii=False, indent=1, sort_keys=True))
    except llm.BudgetExceededError as e:
        print(f"stopped: {e}", file=sys.stderr)

    if args.sample:
        write_pilot(Path("pilot.md"), [c for c in todo if c["id"] in labels], labels)
    print(
        f"labelled {len(done)}; tokens used: {llm.budget.input} input, {llm.budget.output} output",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
