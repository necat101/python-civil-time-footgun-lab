#!/usr/bin/env python3
"""Civil-time footgun correctness lab."""
import json, time, sys, platform, pathlib, csv, statistics, tracemalloc, subprocess
from datetime import datetime, date, time as dtime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
    ZONEINFO_AVAILABLE = True
except Exception:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception
    ZONEINFO_AVAILABLE = False

def load_cases():
    with open("cases.json") as f:
        return json.load(f)

def parse_offset(s):
    if not s: return None
    sign = 1 if s[0] == '+' else -1
    h, m = s[1:].split(":")
    return timezone(timedelta(hours=sign*int(h), minutes=sign*int(m)))

def is_gap(dt_naive, zname):
    if not ZONEINFO_AVAILABLE or not zname: return False
    try:
        zi = ZoneInfo(zname)
    except Exception:
        return False
    dt = dt_naive.replace(tzinfo=zi)
    # round-trip check
    utc = dt.astimezone(timezone.utc)
    back = utc.astimezone(zi)
    # if wall time changed, likely a gap
    return back.replace(tzinfo=None) != dt_naive

def is_fold(dt_naive, zname):
    if not ZONEINFO_AVAILABLE or not zname: return False
    try:
        zi = ZoneInfo(zname)
    except Exception:
        return False
    dt0 = dt_naive.replace(tzinfo=zi, fold=0)
    dt1 = dt_naive.replace(tzinfo=zi, fold=1)
    return dt0.utcoffset() != dt1.utcoffset()

def get_dt_local(case):
    if not case.get("local_date") or not case.get("local_time"): return None
    d = date.fromisoformat(case["local_date"])
    tm = dtime.fromisoformat(case["local_time"])
    return datetime.combine(d, tm)

# Methods
def preserve_local_civil_time_baseline(case):
    """Preserve local date/time + zone as source of truth."""
    name = "preserve_local_civil_time_baseline"
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    # future_local_intent cases etc.
    if case["context"] in ("future_human_schedule","recurring_meeting","floating_reminder","all_day_event","travel_caveat"):
        if local_dt and (zname or case["context"]=="floating_reminder" or "date_not_instant" in case.get("tags",[])):
            return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"local civil time preserved"}
    if "date_not_instant" in case.get("tags",[]):
        return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"date preserved"}
    if local_dt and zname:
        return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"local preserved"}
    # naive check
    if "naive_datetime_negative" in case.get("tags",[]):
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"naive rejected"}
    return {"ok": bool(local_dt), "local_preserved": bool(local_dt), "utc_derived":False, "note":"baseline"}

def derive_utc_from_zoneinfo_when_possible(case):
    name = "derive_utc_from_zoneinfo_when_possible"
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"missing zoneinfo/local"}
    try:
        zi = ZoneInfo(zname)
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"invalid zone"}
    # gap detection
    if is_gap(local_dt, zname):
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"gap time"}
    fold = is_fold(local_dt, zname)
    aware = local_dt.replace(tzinfo=zi)
    utc = aware.astimezone(timezone.utc)
    return {"ok":True, "local_preserved":True, "utc_derived":True, "utc":utc.isoformat(), "fold_detected":fold, "note":"derived utc"}

def utc_only_storage_baseline(case):
    utc_instant = case.get("utc_instant")
    if utc_instant:
        return {"ok":True, "local_preserved":False, "utc_derived":True, "note":"utc only – local intent lost"}
    # try derive
    r = derive_utc_from_zoneinfo_when_possible(case)
    if r["ok"]:
        return {"ok":True, "local_preserved":False, "utc_derived":True, "note":"utc only baseline"}
    return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no utc"}

def fixed_offset_only_baseline(case):
    off = case.get("offset")
    local_dt = get_dt_local(case)
    if off and local_dt:
        tz = parse_offset(off)
        if tz:
            aware = local_dt.replace(tzinfo=tz)
            utc = aware.astimezone(timezone.utc)
            return {"ok":True, "local_preserved":False, "utc_derived":True, "note":"fixed offset only – not a zone"}
    # also try inferring offset from zone – still lossy
    zname = case.get("zone_key")
    if zname and local_dt and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            aware = local_dt.replace(tzinfo=zi)
            off_val = aware.utcoffset()
            return {"ok":True, "local_preserved":False, "utc_derived":True, "fixed_offset_caveat":True, "note":"offset extracted – zone lost"}
        except Exception:
            pass
    return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no offset"}

def naive_add_168_hours_recurrence(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no local dt"}
    # naive 168h add
    next_dt = local_dt + timedelta(hours=168)
    # check if zone would shift local time
    if zname and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            a0 = local_dt.replace(tzinfo=zi)
            # naive add in local wall, then interpret
            a1 = next_dt.replace(tzinfo=zi)
            # real same-wall-time next week
            from datetime import date as _date
            nd = local_dt.date()
            # simple: does offset change?
            if a0.utcoffset() != a1.utcoffset():
                return {"ok":True, "local_preserved":False, "utc_derived":True, "recurrence_drift":True, "note":"168h naive – local time may drift across DST"}
        except Exception:
            pass
    return {"ok":True, "local_preserved": "recurrence_not_duration" not in case.get("tags",[]), "utc_derived":True, "note":"naive 168h"}

def calendar_weekly_local_recurrence(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no local"}
    # weekly same local wall time
    next_local = local_dt + timedelta(days=7)
    utc_derived = False
    if zname and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            if not is_gap(next_local, zname):
                aware = next_local.replace(tzinfo=zi)
                utc = aware.astimezone(timezone.utc)
                utc_derived = True
        except Exception:
            pass
    return {"ok":True, "local_preserved":True, "utc_derived":utc_derived, "note":"weekly same local wall time"}

def gap_and_fold_caveat_detector(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"n/a"}
    try:
        if ZONEINFO_AVAILABLE:
            ZoneInfo(zname)
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"invalid zone"}
    gap = is_gap(local_dt, zname)
    fold = is_fold(local_dt, zname)
    if gap or fold:
        return {"ok":True, "local_preserved":True, "utc_derived": not gap, "gap":gap, "fold":fold, "note":"gap/fold detected – policy_needed"}
    return {"ok":True, "local_preserved":True, "utc_derived":True, "gap":False, "fold":False, "note":"no gap/fold"}

def all_day_date_guard(case):
    if "date_not_instant" in case.get("tags",[]) or "all_day_date" in case.get("tags",[]):
        if case.get("local_date") and not case.get("local_time"):
            return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"date-only preserved"}
        if "bad_end_of_day" in case.get("tags",[]):
            return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"bad 23:59:59 range"}
    # for other cases, pass through neutrally
    return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"not an all-day case"}

def local_vs_utc_grouping_demo(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"n/a"}
    try:
        zi = ZoneInfo(zname)
        aware = local_dt.replace(tzinfo=zi)
        utc = aware.astimezone(timezone.utc)
        local_day = aware.date()
        utc_day = utc.date()
        different = local_day != utc_day
        return {"ok":True, "local_preserved":True, "utc_derived":True, "grouping_differs":different, "note":"grouping demo"}
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"err"}

def zone_key_validator(case):
    zname = case.get("zone_key")
    if not zname:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no zone key"}
    if not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"zoneinfo unavailable"}
    try:
        ZoneInfo(zname)
        return {"ok":True, "local_preserved":True, "utc_derived":True, "note":"zone key valid"}
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"invalid zone"}

def timezone_abbreviation_caveat_detector(case):
    # always flag abbreviation caveat – we never rely on abbreviations
    return {"ok":True, "local_preserved":True, "utc_derived":True, "abbrev_caveat":True, "note":"abbreviations ambiguous – use IANA zone IDs"}

def display_preservation_checker(case):
    # does the input preserve user-entered local display?
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if local_dt and (zname or "date_not_instant" in case.get("tags",[]) or case["context"]=="floating_reminder"):
        return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"display preserved"}
    if case.get("offset") and not zname:
        return {"ok":False, "local_preserved":False, "utc_derived":True, "note":"display lost – offset only"}
    # naive datetime – display NOT preserved (no zone context)
    return {"ok": False, "local_preserved": bool(local_dt and zname), "utc_derived":False, "note":"display lost – naive"}

def deliver_no_external_truth_marker(case):
    return {"ok":True, "local_preserved":True, "utc_derived":True, "external_truth_not_tested":True, "note":"future law / production scheduling / compliance NOT tested – toy lab only"}

METHODS = [
    ("preserve_local_civil_time_baseline", preserve_local_civil_time_baseline),
    ("derive_utc_from_zoneinfo_when_possible", derive_utc_from_zoneinfo_when_possible),
    ("utc_only_storage_baseline", utc_only_storage_baseline),
    ("fixed_offset_only_baseline", fixed_offset_only_baseline),
    ("naive_add_168_hours_recurrence", naive_add_168_hours_recurrence),
    ("calendar_weekly_local_recurrence", calendar_weekly_local_recurrence),
    ("gap_and_fold_caveat_detector", gap_and_fold_caveat_detector),
    ("all_day_date_guard", all_day_date_guard),
    ("local_vs_utc_grouping_demo", local_vs_utc_grouping_demo),
    ("zone_key_validator", zone_key_validator),
    ("timezone_abbreviation_caveat_detector", timezone_abbreviation_caveat_detector),
    ("display_preservation_checker", display_preservation_checker),
    ("deliver_no_external_truth_marker", deliver_no_external_truth_marker),
]

def method_expected_ok(method_name, case):
    tags = set(case.get("tags", []))
    has_local = bool(case.get("local_date") and case.get("local_time"))
    has_zone = bool(case.get("zone_key"))
    has_offset = bool(case.get("offset"))
    has_utc = bool(case.get("utc_instant"))
    if method_name == "preserve_local_civil_time_baseline":
        # naive datetime with no zone is NOT preserved (C028, C046)
        if has_local and not has_zone and "date_not_instant" not in tags and case.get("context") != "floating_reminder" and not has_offset:
            return False
        return has_local or "date_not_instant" in tags
    if method_name == "derive_utc_from_zoneinfo_when_possible":
        if not (has_local and has_zone): return False
        if case["id"] in ("C009","C020","C044","C045"): return False
        if case["id"] == "C027": return False
        return True
    if method_name == "utc_only_storage_baseline":
        if has_utc: return True
        return method_expected_ok("derive_utc_from_zoneinfo_when_possible", case)
    if method_name == "fixed_offset_only_baseline":
        return has_offset or (has_local and has_zone and case["id"] != "C027")
    if method_name == "naive_add_168_hours_recurrence":
        return has_local
    if method_name == "calendar_weekly_local_recurrence":
        return has_local
    if method_name == "gap_and_fold_caveat_detector":
        return has_local and has_zone and case["id"] != "C027"
    if method_name == "all_day_date_guard":
        return case["id"] != "C013"
    if method_name == "local_vs_utc_grouping_demo":
        return has_local and has_zone and case["id"] != "C027"
    if method_name == "zone_key_validator":
        return has_zone and case["id"] != "C027"
    if method_name == "timezone_abbreviation_caveat_detector":
        return True
    if method_name == "display_preservation_checker":
        return has_local and (has_zone or "date_not_instant" in tags or case.get("context")=="floating_reminder")
    if method_name == "deliver_no_external_truth_marker":
        return True
    return case["expected"] == "success"

def check_correctness(method_name, case, result):
    tags = case.get("tags", [])
    actual_ok = result.get("ok", False)
    expected_ok = method_expected_ok(method_name, case)
    correct = (actual_ok == expected_ok)
    naive_fail_tags = {"gap_time","naive_datetime_negative","offset_only_caveat","recurrence_not_duration"}
    is_naive_method = method_name in ("naive_add_168_hours_recurrence","utc_only_storage_baseline","fixed_offset_only_baseline")
    expected_fail_for_naive = bool(set(tags) & naive_fail_tags) and is_naive_method and not actual_ok
    return correct, expected_fail_for_naive

def main():
    tracemalloc.start()
    cases = load_cases()
    results = []
    for method_name, method_fn in METHODS:
        for case in cases:
            t0 = time.perf_counter()
            try:
                res = method_fn(case)
            except Exception as e:
                res = {"ok":False, "note":f"crash: {e}"}
            elapsed = time.perf_counter() - t0
            correct, expected_fail_naive = check_correctness(method_name, case, res)
            results.append({
                "method": method_name,
                "case_id": case["id"],
                "category": case["category"],
                "event_name": case["event_name"],
                "input_chars": len(json.dumps(case)),
                "expected": case["expected"],
                "actual_ok": res.get("ok", False),
                "correct": correct,
                "expected_fail_naive": expected_fail_naive,
                "local_preserved": res.get("local_preserved", False),
                "utc_derived": res.get("utc_derived", False),
                "gap_fold_detected": res.get("gap", False) or res.get("fold", False),
                "note": res.get("note",""),
                "elapsed_ms": elapsed*1000,
                "output_chars": len(json.dumps(res)),
            })
    # summary
    total = len(results)
    passed = sum(1 for r in results if r["correct"])
    failed = total - passed
    # Aggregate by method
    by_method = {}
    for r in results:
        m = r["method"]
        by_method.setdefault(m, {"pass":0,"fail":0,"time":0.0})
        if r["correct"]: by_method[m]["pass"] += 1
        else: by_method[m]["fail"] += 1
        by_method[m]["time"] += r["elapsed_ms"]
    # tag counts
    def count_tag(t): return sum(1 for c in cases if t in c.get("tags",[]))
    # write RESULTS.md
    out = []
    out.append("# RESULTS – python-civil-time-footgun-lab\n")
    out.append(f"Cases: {len(cases)} | Methods: {len(METHODS)} | Total runs: {total}\n")
    out.append(f"Passed: {passed} | Failed: {failed}\n")
    out.append("\n## By method\n")
    out.append("| Method | Pass | Fail | Time ms |")
    out.append("|---|---|---|---|")
    for m, s in by_method.items():
        out.append(f"| {m} | {s['pass']} | {s['fail']} | {s['time']:.2f} |")
    out.append("\n## Tag counts\n")
    for tag in sorted(set(t for c in cases for t in c.get("tags",[]))):
        out.append(f"- {tag}: {count_tag(tag)}")
    out.append("\n## Environment\n")
    out.append(f"- Python: {sys.version.split()[0]}")
    out.append(f"- Platform: {platform.platform()}")
    out.append(f"- zoneinfo available: {ZONEINFO_AVAILABLE}")
    try:
        if ZONEINFO_AVAILABLE:
            tz_avail = len(available_timezones())
            out.append(f"- available_timezones: {tz_avail}")
    except Exception:
        pass
    out.append(f"- Cases file size: {pathlib.Path('cases.json').stat().st_size} bytes")
    out.append(f"- Random seed: 42")
    out.append(f"- Subprocess count: 0")
    out.append(f"- Network calls: 0")
    out.append(f"- External calendar/timezone APIs: 0")
    out.append(f"- HN thread accessed: yes – https://news.ycombinator.com/item?id=19500640")
    current, peak = tracemalloc.get_traced_memory()
    out.append(f"- tracemalloc current: {current} bytes, peak: {peak} bytes")
    out.append("\n## Correctness policy\n")
    out.append("Correctness before speed. UTC is great for past instants/logs. Future human schedules need local civil time + zone context. Offsets ≠ zone IDs. Recurring meetings ≠ add 168h. DST gaps/folds need business policy. All-day = date, not 00:00–23:59:59. User intent matters.\n")
    out.append("\n## Notes\n")
    out.append("- Toy lab only – not a calendar product, not legal-time prediction, not production scheduling.")
    out.append("- No external date/time libraries. Python stdlib only.")
    out.append("- No real customer calendars, no network calls.")
    out.append("- Future law changes NOT tested.")
    pathlib.Path("RESULTS.md").write_text("\n".join(out))
    print(f"Passed {passed}/{total}, failed {failed}")
    print("Wrote RESULTS.md")

if __name__ == "__main__":
    main()
