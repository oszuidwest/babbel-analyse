# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W23, n=53):**

- 68% accurate
- 25% edited
- 8% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=e54e375f)

![Mean word count AI vs. published per week](chart-words.svg?v=1f0dd560)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W23 | 53 | 68% | 25% | 8% | 62 | 64 |
| 2026-W22 | 45 | 40% | 42% | 18% | 62 | 64 |
| 2026-W21 | 56 | 68% | 30% | 2% | 64 | 64 |
| 2026-W20 | 50 | 50% | 34% | 16% | 63 | 65 |
| 2026-W19 | 52 | 62% | 33% | 6% | 60 | 61 |
| 2026-W18 | 62 | 52% | 42% | 6% | 60 | 62 |
| 2026-W17 | 52 | 56% | 42% | 2% | 63 | 63 |
| 2026-W16 | 55 | 55% | 44% | 2% | 63 | 63 |
| 2026-W15 | 49 | 27% | 10% | 63% | 65 | 63 |
| 2026-W14 | 56 | 18% | 9% | 73% | 68 | 63 |
| 2026-W13 | 51 | 2% | 14% | 84% | 108 | 69 |
| 2026-W12 | 59 | 5% | 2% | 93% | 102 | 69 |
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
