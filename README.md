# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W46, n=48):**

- 27% accurate
- 46% edited
- 27% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=98ac03c1)

![Mean word count AI vs. published per week](chart-words.svg?v=0defdd3b)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W46 | 48 | 27% | 46% | 27% | 64 | 68 |
| 2026-W45 | 58 | 45% | 45% | 10% | 64 | 66 |
| 2026-W44 | 58 | 48% | 43% | 9% | 63 | 65 |
| 2026-W43 | 40 | 38% | 30% | 32% | 63 | 65 |
| 2026-W42 | 60 | 53% | 37% | 10% | 64 | 65 |
| 2026-W41 | 49 | 69% | 20% | 10% | 63 | 65 |
| 2026-W40 | 54 | 43% | 44% | 13% | 64 | 66 |
| 2026-W39 | 63 | 60% | 32% | 8% | 63 | 65 |
| 2026-W38 | 52 | 67% | 23% | 10% | 64 | 64 |
| 2026-W37 | 48 | 40% | 42% | 19% | 63 | 65 |
| 2026-W36 | 38 | 55% | 24% | 21% | 63 | 65 |
| 2026-W35 | 48 | 67% | 19% | 15% | 63 | 64 |
<!-- END:STATS -->

## Kinds of change

`label.py` asks a model what kind of change the editors made to each edited story (over 5%
of words changed): a fact fixed, something missing from the article added, information
added that is not in the article, timing, a style rule or taste. One story can have several
kinds. The labels are kept per story in `labels.json`, so each story is labelled once. A
story is labelled again only when its texts change or the classifier changes.

The model needs the article the AI worked from. New stories carry it in their Babbel
metadata. For older stories, `--articles` takes the text rebuilt from WordPress revisions.

The kinds only show up in the table after an editor has checked a sample: run
`label.py --sample 40`, have an editor check `pilot.md`, and list the kinds that hold up in
`PUBLISHED_KINDS` in `update_readme.py`. A week shows a dash for a kind when fewer than 80%
of its edited stories have a label.

Every run that calls OpenAI stops when it has used `MAX_INPUT_TOKENS` or
`MAX_OUTPUT_TOKENS`, as reported by OpenAI.

## Running locally

```sh
export BABBEL_USERNAME=...
export BABBEL_PASSWORD=...
python3 fetch_all.py   # writes stories.json
python3 analyze.py     # writes weekly.json
```

## Secrets

- `BABBEL_USERNAME`
- `BABBEL_PASSWORD`
- `OPENAI_API_KEY`: for labelling the kinds of change
