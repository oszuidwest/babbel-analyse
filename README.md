# babbel-analyse

Weekly quality measurement of the AI-generated read-aloud text in [Babbel](https://github.com/oszuidwest/zwfm-babbel).
Compares `metadata.original_speech_text` (AI output) to `text` (after editing) and aggregates per ISO week in `weekly.json`. Only stories that finished airing and were not deleted count.

A GitHub Action runs every Monday night at 03:00 NL time, refreshes the data and commits `weekly.json` if anything changed.

<!-- BEGIN:STATS -->
## Latest results

**Last week (2026-W47, n=35):**

- 43% accurate
- 54% edited
- 3% rewritten

![Share of accurate / edited / rewritten per week](chart-buckets.svg?v=b7f0b9a2)

![Mean word count AI vs. published per week](chart-words.svg?v=c7197824)

| Week | n | % accurate | % edited | % rewritten | Words AI | Words pub. | % AI > 65 | % pub. > 65 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-W47 | 35 | 43% | 54% | 3% | 63 | 67 | 0% | 43% |
| 2026-W46 | 48 | 27% | 46% | 27% | 64 | 68 | 6% | 62% |
| 2026-W45 | 55 | 42% | 47% | 11% | 64 | 66 | 2% | 40% |
| 2026-W44 | 58 | 48% | 43% | 9% | 63 | 65 | 7% | 43% |
| 2026-W43 | 39 | 36% | 31% | 33% | 63 | 65 | 5% | 38% |
| 2026-W42 | 57 | 51% | 39% | 11% | 63 | 65 | 4% | 40% |
| 2026-W41 | 49 | 69% | 20% | 10% | 63 | 65 | 4% | 31% |
| 2026-W40 | 53 | 42% | 45% | 13% | 64 | 66 | 8% | 38% |
| 2026-W39 | 61 | 59% | 33% | 8% | 63 | 65 | 3% | 30% |
| 2026-W38 | 51 | 67% | 24% | 10% | 64 | 64 | 10% | 24% |
| 2026-W37 | 47 | 38% | 43% | 19% | 63 | 66 | 4% | 40% |
| 2026-W36 | 35 | 51% | 26% | 23% | 64 | 65 | 11% | 29% |
<!-- END:STATS -->

## Kinds of change

`label.py` labels the kinds of change (see `KINDS`) in each finished story of the last 92
days with over 5% of words changed, into `labels.json`. A run makes at most `MAX_CALLS`
calls (default 5), each with a capped article and answer. A week shows a kind only when
all its edited stories have a label, and only for kinds in `PUBLISHED_KINDS`, which stays
empty until an editor has checked a sample. Older stories need `--articles`, the articles
rebuilt from WordPress revisions; without an article a story stays unlabelled.

## Monthly prompt check

`speech-prompt.txt` is the prompt that is live in the Knabbel plugin. On the first of the
month, `tune.py` takes the stories of the last 35 days made with that prompt (the plugin
records the article and prompt in `metadata.generation`), asks a model for a better prompt
from the edited ones, and tests both prompts on the newest 40 stories with the production
model. A model compares each pair blindly with the broadcast text and checks both against
the article. The new prompt wins only when it is better often enough to rule out luck
(sign test, p < 0.05), with no more unsupported statements or texts over 70 words. Then
the workflow opens a pull request; otherwise it saves the report in `reports/`. A run
makes at most 121 calls (the cap is 130) and skips very long stories and proposals, which
bounds what it sends. The prompt diff in the pull request is the check that a new prompt
keeps the newsroom's rules.

Merging puts the prompt live through the plugin's REST route. The deploy only replaces a
prompt that was once committed here, so restoring an older committed prompt by hand in
WordPress does not stop it. If the live prompt was changed by hand, the deploy stops. To
keep that change, commit it as `speech-prompt.txt`, then commit the new prompt again. To
drop it, put a committed version back in WordPress and rerun the deploy workflow.

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
- `OPENAI_API_KEY`: for `label.py` and `tune.py`
- `WP_PROMPT_USER`, `WP_PROMPT_PASSWORD`: a WordPress user with the Knabbel prompt bot
  role and an application password, for the deploy
