# RESULTS – python-civil-time-footgun-lab

Cases: 48 | Methods: 13 | Total runs: 624

Passed: 624 | Failed: 0


Detailed per-method/per-case records: [`results_rows.csv`](results_rows.csv) / [`results_rows.json`](results_rows.json)


## By method

| Method | Pass | Fail | Time ms |
|---|---|---|---|
| preserve_local_civil_time_baseline | 48 | 0 | 0.32 |
| derive_utc_from_zoneinfo_when_possible | 48 | 0 | 113.89 |
| utc_only_storage_baseline | 48 | 0 | 10.43 |
| fixed_offset_only_baseline | 48 | 0 | 10.00 |
| naive_add_168_hours_recurrence | 48 | 0 | 9.74 |
| calendar_weekly_local_recurrence | 48 | 0 | 10.05 |
| gap_and_fold_caveat_detector | 48 | 0 | 10.23 |
| all_day_date_guard | 48 | 0 | 0.08 |
| local_vs_utc_grouping_demo | 48 | 0 | 9.15 |
| zone_key_validator | 48 | 0 | 8.01 |
| timezone_abbreviation_caveat_detector | 48 | 0 | 0.04 |
| display_preservation_checker | 48 | 0 | 0.33 |
| deliver_no_external_truth_marker | 48 | 0 | 0.05 |

## Tag counts

- all_day_date: 2
- aware_datetime: 4
- bad_end_of_day: 1
- business_rule_needed: 9
- date_not_instant: 4
- display_loss: 3
- fixed_offset_caveat: 3
- fold_policy_needed: 7
- fold_time: 5
- future_local_intent: 7
- gap_time: 4
- invalid_zone: 1
- leap_year_caveat: 1
- midnight_boundary: 2
- month_length_caveat: 2
- naive_datetime_negative: 2
- non_hour_offset: 3
- offset_only_caveat: 4
- recurrence_not_duration: 8
- sorting_grouping_caveat: 4
- timezone_abbreviation_caveat: 1
- utc_good_for_past_instant: 3
- utc_only_loses_context: 1
- weekly_dst: 3
- zone_id_preserved: 10

## Environment

- Python: 3.12.3
- Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
- zoneinfo available: True
- available_timezones: 599
- Cases file size: 24484 bytes
- Random seed: 42
- Subprocess count: 0
- Network calls: 0
- External calendar/timezone APIs: 0
- HN thread accessed: yes – https://news.ycombinator.com/item?id=19500640
  - Evidence: [`hn_thread_evidence.md`](hn_thread_evidence.md)
- tracemalloc current: 2750356 bytes, peak: 2826732 bytes

## Correctness policy

Correctness before speed. UTC is great for past instants/logs. Future human schedules need local civil time + zone context. Offsets ≠ zone IDs. Recurring meetings ≠ add 168h. DST gaps/folds need business policy. All-day = date, not 00:00–23:59:59. User intent matters.


Correctness scoring validates: expected ok status, local_preserved, utc_derived, gap/fold detection, recurrence_ok, all_day_ok, display_preserved, grouping_differs, zone_valid, abbrev_caveat, external_truth_not_tested – per method.


## Notes

- Toy lab only – not a calendar product, not legal-time prediction, not production scheduling.
- No external date/time libraries. Python stdlib only.
- No real customer calendars, no network calls.
- Future law changes NOT tested.