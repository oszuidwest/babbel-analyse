# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W26, n=45):**

- 51% accurate
- 36% edited
- 13% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=b57da55d)

![Mean word count AI vs. published per week](chart-words.svg?v=74097a9f)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W26 | 45 | 51% | 36% | 13% | 60 | 63 |
| 2026-W25 | 53 | 49% | 38% | 13% | 63 | 64 |
| 2026-W24 | 52 | 62% | 31% | 8% | 63 | 64 |
| 2026-W23 | 53 | 68% | 25% | 8% | 62 | 64 |
| 2026-W22 | 45 | 40% | 42% | 18% | 62 | 64 |
| 2026-W21 | 56 | 68% | 30% | 2% | 64 | 64 |
| 2026-W20 | 50 | 50% | 34% | 16% | 63 | 65 |
| 2026-W19 | 52 | 62% | 33% | 6% | 60 | 61 |
| 2026-W18 | 62 | 52% | 42% | 6% | 60 | 62 |
| 2026-W17 | 52 | 56% | 42% | 2% | 63 | 63 |
| 2026-W16 | 55 | 55% | 44% | 2% | 63 | 63 |
| 2026-W15 | 49 | 27% | 10% | 63% | 65 | 63 |
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
