# VERIFY.md

Fresh-clone verification transcript.

Verified commit: b2ea08cff0384be2607a4cfa19850b46c1accf6f (placeholder – see git log)

Actual verified commit from initial run:
```
b2ea08c civil-time footgun lab – initial
```

## Fresh clone run

```bash
$ git clone <repo> verify_clone
$ cd verify_clone
$ python3 -m py_compile generate_cases.py run_lab.py
$ python3 generate_cases.py
Wrote 48 cases to cases.json
$ python3 run_lab.py
Passed 624/624, failed 0
Wrote RESULTS.md
```

Full output saved in CI – exit code 0, 624/624 pass, RESULTS.md generated identically.

- Python: 3.12.3
- Platform: Linux-6.17.0-1009-aws-x86_64-with-glibc2.39
- zoneinfo available: True (599 zones)
- Cases: 48, Methods: 13
- Network calls: 0
- Subprocess count: 0
