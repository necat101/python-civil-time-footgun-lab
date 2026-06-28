# HN Thread Access Evidence

HN thread read via the Hacker News CLI tool (`hackernews get-item`) **before** writing README.md.

## Thread

- **ID:** 19500640
- **Title:** "Storing UTC is not a silver bullet"
- **URL:** https://news.ycombinator.com/item?id=19500640
- **Linked article:** https://codeblog.jonskeet.uk/2019/03/27/storing-utc-is-not-a-silver-bullet/
- **Score:** 304 | **Comments:** 162
- **Posted:** 2019-03-27

## Access method

```bash
python3 ./hackernews get-item --id 19500640
```

Followed by fetching top-level comments individually:

```bash
python3 ./hackernews get-item --id 19501110  # rlpb – alarm clock problem
python3 ./hackernews get-item --id 19502802  # sudhirj – past instants vs future wall clock
python3 ./hackernews get-item --id 19502213  # reaperducer – people × time = mess
python3 ./hackernews get-item --id 19501588  # lmm – system times vs human times
python3 ./hackernews get-item --id 19503082  # ble – civil vs atomic vs sidereal time
python3 ./hackernews get-item --id 19503470  # jrochkind1 – future dates + TZ rule changes
python3 ./hackernews get-item --id 19503164  # amenod – past UTC, future local
python3 ./hackernews get-item --id 19501870  # kuon – wall clock + user location
python3 ./hackernews get-item --id 19501576  # argd678 – birthdays are timezone-affected
python3 ./hackernews get-item --id 19502830  # kazinator – countdown timer paradox
python3 ./hackernews get-item --id 19501993  # barrystaes – store everything in UTC
python3 ./hackernews get-item --id 19506767  # EGreg – recurring events, DST
# … and ~20 more comments
```

Raw API responses saved in this repo:
- `hn_thread_19500640.json` – story metadata
- `hn_comments_sample.jsonl` – 12 top comment bodies

The README.md sentiment summary was written from these actual HN comments, not from the linked article alone or from web search summaries.

## Date accessed

2026-06-28, before initial README.md commit (b2ea08c).
