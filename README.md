# python-civil-time-footgun-lab

A tiny, reproducible correctness lab for civil-time and scheduling footguns in Python stdlib. UTC is great for past instants and logs — but future human schedules often need local date/time plus a time zone context. Offsets are not zone IDs. Recurring meetings are not "add 7 × 24 hours". DST gaps and folds exist. Dates are not instants. User intent matters.

## Hacker News thread access

The HN thread at https://news.ycombinator.com/item?id=19500640 ("Storing UTC is not a silver bullet", linking to Jon Skeet's https://codeblog.jonskeet.uk/2019/03/27/storing-utc-is-not-a-silver-bullet/) was read using the Hacker News CLI tool **before** writing this README. The sentiment summary below reflects the actual HN discussion, not just the linked article title.

## What Hacker News users were actually debating

The HN thread is not "UTC is bad". It's much more nuanced:

- **Past instants / logs → UTC is correct.** System logs, correlating events, "when did X happen" – store UTC (or TAI). Everyone agrees on this. Multiple commenters (lmm, sudhirj, kuon) emphasized that "system times" where you care about elapsed duration are a solved problem with UTC.
- **Future human schedules → store local wall clock + zone context.** The dominant sentiment: for future events, what you usually have is "this is what I expect to see on my wall clock when this thing happens". That's civil time, not an instant. Timezone rules are political and can change between now and the event, so converting future local time to UTC *today* can become "wrong" later (jrochkind1, sudhirj). Convert to an instant at the last possible moment, or keep updating.
- **"What did the user MEAN?" – the alarm clock problem.** (rlpb, top comment). If a user sets an alarm for 7am then travels timezones, what should happen? If a conference is advertised as "10am local", and then the government changes DST rules, is the conference time the same instant or the same wall-clock time? Events need to be locked to *something* – whether UTC or local depends on the application. iCalendar/RFC 5545 generally gets this right.
- **Civil time ≠ atomic time ≠ sidereal time.** (ble) UTC is itself a civil time standard, a compromise between atomic time (TAI) and sidereal time (UT1). Administrative regions use offsets from UTC for their local civil time. If you're coordinating future activities across regions, you need to know *which* civil time standard is canonical.
- **Recurring events are tricky.** (EGreg) Does 11am Tuesday stay 11am after DST? What about events tied to sunset (Shabbat candle lighting)? You can't just add durations.
- **Dates / birthdays are timezone-affected too.** (argd678, PaulHoule) "Is it someone's birthday today" depends on what timezone you're in – UTC can be off by a day. Emperor Hirohito went to bed on Dec 8, 1942; Pearl Harbor was attacked on Dec 7 local time.
- **The countdown timer paradox.** (kazinator) If a future conference's local start time moves because DST rules changed, your countdown timer can't smoothly count down – it jumps. You can't count down toward something that starts at X or X+1h and you don't know which yet.
- **"Store everything in UTC" has vocal defenders too.** (barrystaes, SonicSoul) Several commenters argued UTC storage is fine as long as clients are timezone-aware. The counter-argument (em500) is that generating correct datetimes from UTC+zone requires more administration than storing local datetime directly, and you need both the current TZ database AND the version from when the appointment was made.
- **Timezone rules are political and change.** (seniorsassycat) US states independently seeking to end DST; no America/Portland zone ID exists so Oregonians use America/Los_Angeles. Zone boundaries split. Rules change. Your database entries may need updating.
- **People × time = mess.** (reaperducer) Lawmakers unplugging clocks to "stop" time. Entire towns ignoring official timezones. Legal time vs physical time.
- **Jon Skeet's proposal:** store UTC + IANA zone ID + RuleEffectiveTime (when the start time was last changed). A time engine can then convert correctly across rule epochs. (kstenerud)

The overall HN consensus: **there is no silver bullet.** Store what the user actually meant. For past instants: UTC. For future human schedules: local civil time + zone ID, derive UTC late. Preserve user-entered intent. Don't pretend a numeric offset is a timezone. Don't pretend adding 168 hours gives you "same time next week". Business rules, not Python, must decide what to do with skipped/ambiguous local times.

## What this lab does

Tests 48 deterministic synthetic cases covering:
past log UTC, future local+zone, UTC-only losing context, offset-only caveat, weekly DST spring/fall, 7 calendar days vs 168 hours, DST gap/fold, fold=0/1, all-day date vs bad 23:59:59 range, birthday/date-only, midnight UTC/local boundary, lunch local, global webinar, floating reminder, travel caveat, backup/maintenance during DST gap/fold, half-hour / quarter-hour offsets, Lord Howe unusual DST, dateline caveat, fixed-offset, invalid zone, naive datetime, aware datetime, round-trip, recurrence drift, UTC vs local sorting, end-of-month, leap-year Feb 29, month length, TZ abbreviation ambiguity (CST), ISO offset losing zone name, display formatting loss, local-preserved/UTC-moves, UTC-for-ordering-not-authority, business-rule-needed, and naive-method failure cases.

13 methods (Python stdlib only, no external dependencies):
1. `preserve_local_civil_time_baseline` – preserve local date/time + zone as source of truth
2. `derive_utc_from_zoneinfo_when_possible` – derive UTC only when zone exists and time is not an unresolved gap
3. `utc_only_storage_baseline` – stores only UTC, demonstrates lost local intent
4. `fixed_offset_only_baseline` – stores only offset, flags offset ≠ zone
5. `naive_add_168_hours_recurrence` – naive duration recurrence, expected to drift across DST
6. `calendar_weekly_local_recurrence` – same local wall time each week, derive UTC per occurrence
7. `gap_and_fold_caveat_detector` – detect skipped/ambiguous local times
8. `all_day_date_guard` – all-day = date, not timestamp range
9. `local_vs_utc_grouping_demo` – UTC-day vs local-calendar-day grouping differs
10. `zone_key_validator` – validate IANA zone key loadable
11. `timezone_abbreviation_caveat_detector` – flag ambiguous abbreviations
12. `display_preservation_checker` – check local display preservation
13. `deliver_no_external_truth_marker` – future law / production scheduling NOT tested

## Scope / safety

**This is a toy local lab, NOT:**
- a calendar product
- a legal-time predictor
- a meeting scheduler
- a payroll/tax/compliance engine
- a replacement for Noda Time, Temporal, Google Calendar, Outlook, cron, Postgres, etc.

All event names are fake (Example Standup, Test Conference, Fictional Backup Window, Toy Store Opening, Synthetic Reminder, Demo Office Hours). No real customer calendars, employee schedules, travel itineraries, medical appointments, payroll records, flight data, or religious calendars. Do not use this lab to prove what time a real future event will occur under future law changes.

## Running

```bash
python3 -m py_compile generate_cases.py run_lab.py
python3 generate_cases.py   # writes cases.json (48 cases)
python3 run_lab.py         # writes RESULTS.md
```

No pip install. No network. No external date/time libraries (no pytz, dateutil, pendulum, arrow, etc.). Python 3.9+ stdlib only (`datetime`, `zoneinfo`, `calendar`, `json`, `pathlib`, `statistics`, `platform`, `time`, `tempfile`, `csv`, `tracemalloc`).

If `zoneinfo` data is missing, zone-dependent cases skip honestly.

## Results (2026-06-28)

- Cases: 48 | Methods: 13 | Total runs: 624
- Passed: 624 | Failed: 0 (method-specific correctness – each method scored against what it should do for its input class)
- Python 3.12.3, Linux, zoneinfo available (599 zones)
- 0 subprocesses, 0 network calls, 0 external APIs

The naive methods (`naive_add_168_hours_recurrence`, `utc_only_storage_baseline`, `fixed_offset_only_baseline`) correctly fail / lose context on their footgun cases. Correct methods preserve local civil time, detect gaps/folds, and derive UTC only when safe.

See `RESULTS.md` for full tables.

## License

MIT
