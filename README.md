# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W20, n=50):**

- 50% accurate
- 34% edited
- 16% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=0cd32224)

![Mean word count AI vs. published per week](chart-words.svg?v=b0da81ca)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W20 | 50 | 50% | 34% | 16% | 63 | 65 |
| 2026-W19 | 52 | 62% | 33% | 6% | 60 | 61 |
| 2026-W18 | 62 | 52% | 42% | 6% | 60 | 62 |
| 2026-W17 | 52 | 56% | 42% | 2% | 63 | 63 |
| 2026-W16 | 55 | 55% | 44% | 2% | 63 | 63 |
| 2026-W15 | 49 | 27% | 10% | 63% | 65 | 63 |
| 2026-W14 | 56 | 18% | 9% | 73% | 68 | 63 |
| 2026-W13 | 51 | 2% | 14% | 84% | 108 | 69 |
| 2026-W12 | 59 | 5% | 2% | 93% | 102 | 69 |
| 2026-W11 | 59 | 5% | 2% | 93% | 108 | 68 |
| 2026-W10 | 55 | 7% | 15% | 78% | 112 | 69 |
| 2026-W09 | 48 | 12% | 12% | 75% | 107 | 75 |
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
