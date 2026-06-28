# VERIFY.md

Fresh-clone verification – python-civil-time-footgun-lab

## Commit verified

```
b90af4885496f84f9ab00ae0c0c0d3d176276c6e
audit fixes: detailed results_rows.csv/json, HN thread evidence,
improved correctness scoring
```

## Fresh clone transcript

```bash
$ git clone https://github.com/necat101/python-civil-time-footgun-lab.git verify_civil_time
Cloning into 'verify_civil_time'...

$ cd verify_civil_time

$ python3 -m py_compile generate_cases.py run_lab.py
OK

$ python3 generate_cases.py
Wrote 48 cases to cases.json

$ python3 run_lab.py
Passed 624/624, failed 0
Wrote RESULTS.md, results_rows.csv (624 rows), results_rows.json
```

Exit code: 0

## Environment

- Python: 3.12.3
- Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
- zoneinfo available: True (599 zones)
- Cases: 48 | Methods: 13 | Total runs: 624
- Network calls: 0
- Subprocess count: 0

## Artifacts produced

- `cases.json` – 48 deterministic synthetic cases
- `RESULTS.md` – summary tables
- `results_rows.csv` – 624 rows, full per-method/per-case records
- `results_rows.json` – same data as JSON

All artifacts match the committed versions (modulo timestamps / tracemalloc memory counters in RESULTS.md).
