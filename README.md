# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W37, n=48):**

- 40% accurate
- 42% edited
- 19% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=f7316d40)

![Mean word count AI vs. published per week](chart-words.svg?v=6b7c7ddb)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W37 | 48 | 40% | 42% | 19% | 63 | 65 |
| 2026-W36 | 38 | 55% | 24% | 21% | 63 | 65 |
| 2026-W35 | 48 | 67% | 19% | 15% | 63 | 64 |
| 2026-W34 | 41 | 32% | 44% | 24% | 62 | 65 |
| 2026-W33 | 37 | 68% | 27% | 5% | 61 | 60 |
| 2026-W32 | 39 | 69% | 31% | 0% | 61 | 62 |
| 2026-W31 | 45 | 60% | 33% | 7% | 64 | 63 |
| 2026-W30 | 40 | 38% | 40% | 22% | 61 | 66 |
| 2026-W29 | 41 | 44% | 34% | 22% | 64 | 66 |
| 2026-W28 | 51 | 61% | 29% | 10% | 61 | 63 |
| 2026-W27 | 46 | 52% | 33% | 15% | 61 | 62 |
| 2026-W26 | 45 | 51% | 36% | 13% | 60 | 63 |
<!-- END:STATS -->

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
