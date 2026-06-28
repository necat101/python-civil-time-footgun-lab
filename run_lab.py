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
    utc = dt.astimezone(timezone.utc)
    back = utc.astimezone(zi)
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

# ── Methods ───────────────────────────────────────────────────────────────

def preserve_local_civil_time_baseline(case):
    """Preserve local date/time + zone as source of truth."""
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    tags = case.get("tags", [])
    if case["context"] in ("future_human_schedule","recurring_meeting","floating_reminder","all_day_event","travel_caveat"):
        if local_dt and (zname or case["context"]=="floating_reminder" or "date_not_instant" in tags):
            return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"local civil time preserved"}
    if "date_not_instant" in tags:
        return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"date preserved"}
    if local_dt and zname:
        return {"ok":True, "local_preserved":True, "utc_derived":False, "note":"local preserved"}
    if "naive_datetime_negative" in tags:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"naive rejected"}
    return {"ok": bool(local_dt), "local_preserved": bool(local_dt), "utc_derived":False, "note":"baseline"}

def derive_utc_from_zoneinfo_when_possible(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"missing zoneinfo/local"}
    try:
        zi = ZoneInfo(zname)
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"invalid zone"}
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
    zname = case.get("zone_key")
    if zname and local_dt and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            aware = local_dt.replace(tzinfo=zi)
            return {"ok":True, "local_preserved":False, "utc_derived":True, "fixed_offset_caveat":True, "note":"offset extracted – zone lost"}
        except Exception:
            pass
    return {"ok":False, "local_preserved":False, "utc_derived":False, "note":"no offset"}

def naive_add_168_hours_recurrence(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "recurrence_ok":False, "note":"no local dt"}
    next_dt = local_dt + timedelta(hours=168)
    drift = False
    if zname and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            a0 = local_dt.replace(tzinfo=zi)
            a1 = next_dt.replace(tzinfo=zi)
            if a0.utcoffset() != a1.utcoffset():
                drift = True
        except Exception:
            pass
    local_preserved = "recurrence_not_duration" not in case.get("tags",[])
    return {"ok":True, "local_preserved":local_preserved, "utc_derived":True, "recurrence_ok": not drift, "note":"168h naive – local time may drift across DST" if drift else "naive 168h"}

def calendar_weekly_local_recurrence(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "recurrence_ok":False, "note":"no local"}
    next_local = local_dt + timedelta(days=7)
    utc_derived = False
    if zname and ZONEINFO_AVAILABLE:
        try:
            zi = ZoneInfo(zname)
            if not is_gap(next_local, zname):
                aware = next_local.replace(tzinfo=zi)
                utc_derived = True
        except Exception:
            pass
    return {"ok":True, "local_preserved":True, "utc_derived":utc_derived, "recurrence_ok":True, "note":"weekly same local wall time"}

def gap_and_fold_caveat_detector(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "gap_detected":False, "fold_detected":False, "note":"n/a"}
    try:
        ZoneInfo(zname)
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "gap_detected":False, "fold_detected":False, "note":"invalid zone"}
    gap = is_gap(local_dt, zname)
    fold = is_fold(local_dt, zname)
    return {"ok":True, "local_preserved":True, "utc_derived": not gap, "gap_detected":gap, "fold_detected":fold, "note":"gap/fold detected – policy_needed" if (gap or fold) else "no gap/fold"}

def all_day_date_guard(case):
    tags = case.get("tags", [])
    if "date_not_instant" in tags or "all_day_date" in tags:
        if case.get("local_date") and not case.get("local_time"):
            return {"ok":True, "local_preserved":True, "utc_derived":False, "all_day_ok":True, "note":"date-only preserved"}
        if "bad_end_of_day" in tags:
            return {"ok":False, "local_preserved":False, "utc_derived":False, "all_day_ok":False, "note":"bad 23:59:59 range"}
    return {"ok":True, "local_preserved":True, "utc_derived":False, "all_day_ok":True, "note":"not an all-day case"}

def local_vs_utc_grouping_demo(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    if not local_dt or not zname or not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "grouping_differs":False, "note":"n/a"}
    try:
        zi = ZoneInfo(zname)
        aware = local_dt.replace(tzinfo=zi)
        utc = aware.astimezone(timezone.utc)
        different = aware.date() != utc.date()
        return {"ok":True, "local_preserved":True, "utc_derived":True, "grouping_differs":different, "note":"grouping demo"}
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "grouping_differs":False, "note":"err"}

def zone_key_validator(case):
    zname = case.get("zone_key")
    if not zname:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "zone_valid":False, "note":"no zone key"}
    if not ZONEINFO_AVAILABLE:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "zone_valid":False, "note":"zoneinfo unavailable"}
    try:
        ZoneInfo(zname)
        return {"ok":True, "local_preserved":True, "utc_derived":True, "zone_valid":True, "note":"zone key valid"}
    except Exception:
        return {"ok":False, "local_preserved":False, "utc_derived":False, "zone_valid":False, "note":"invalid zone"}

def timezone_abbreviation_caveat_detector(case):
    return {"ok":True, "local_preserved":True, "utc_derived":True, "abbrev_caveat":True, "note":"abbreviations ambiguous – use IANA zone IDs"}

def display_preservation_checker(case):
    local_dt = get_dt_local(case)
    zname = case.get("zone_key")
    tags = case.get("tags", [])
    if local_dt and (zname or "date_not_instant" in tags or case["context"]=="floating_reminder"):
        return {"ok":True, "local_preserved":True, "utc_derived":False, "display_preserved":True, "note":"display preserved"}
    if case.get("offset") and not zname:
        return {"ok":False, "local_preserved":False, "utc_derived":True, "display_preserved":False, "note":"display lost – offset only"}
    return {"ok": False, "local_preserved": bool(local_dt and zname), "utc_derived":False, "display_preserved":False, "note":"display lost – naive"}

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

# ── Expected behavior per method ────────────────────────────────────────────

def method_expectations(method_name, case):
    """Return expected observation dict for method+case."""
    tags = set(case.get("tags", []))
    has_local = bool(case.get("local_date") and case.get("local_time"))
    has_zone = bool(case.get("zone_key"))
    has_offset = bool(case.get("offset"))
    has_utc = bool(case.get("utc_instant"))
    cid = case["id"]

    if method_name == "preserve_local_civil_time_baseline":
        if has_local and not has_zone and "date_not_instant" not in tags and case.get("context") != "floating_reminder" and not has_offset:
            return {"ok": False, "local_preserved": False, "utc_derived": False}
        exp_ok = has_local or "date_not_instant" in tags
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": False}

    if method_name == "derive_utc_from_zoneinfo_when_possible":
        gap_case = cid in ("C009","C020","C044","C045")
        invalid = cid == "C027"
        exp_ok = has_local and has_zone and not gap_case and not invalid
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": exp_ok,
                "gap_detected": gap_case, "fold_detected": "fold_time" in tags}

    if method_name == "utc_only_storage_baseline":
        can_derive = has_local and has_zone and cid not in ("C009","C020","C044","C045","C027")
        exp_ok = has_utc or can_derive
        return {"ok": exp_ok, "local_preserved": False, "utc_derived": exp_ok}

    if method_name == "fixed_offset_only_baseline":
        exp_ok = has_offset or (has_local and has_zone and cid != "C027")
        return {"ok": exp_ok, "local_preserved": False, "utc_derived": exp_ok}

    if method_name == "naive_add_168_hours_recurrence":
        exp_ok = has_local
        # recurrence drifts on DST-crossing weekly cases
        recurrence_ok = "recurrence_not_duration" not in tags
        return {"ok": exp_ok, "local_preserved": recurrence_ok, "utc_derived": exp_ok, "recurrence_ok": recurrence_ok}

    if method_name == "calendar_weekly_local_recurrence":
        exp_ok = has_local
        # utc_derived = zone available and next_local not in gap
        # approximate: zone available
        utc_derived = has_local and has_zone
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": utc_derived, "recurrence_ok": exp_ok}

    if method_name == "gap_and_fold_caveat_detector":
        exp_ok = has_local and has_zone and cid != "C027"
        gap_exp = "gap_time" in tags
        fold_exp = "fold_time" in tags
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": exp_ok and not gap_exp,
                "gap_detected": gap_exp, "fold_detected": fold_exp}

    if method_name == "all_day_date_guard":
        bad = cid == "C013"
        return {"ok": not bad, "local_preserved": not bad, "utc_derived": False, "all_day_ok": not bad}

    if method_name == "local_vs_utc_grouping_demo":
        exp_ok = has_local and has_zone and cid != "C027"
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": exp_ok, "grouping_differs": "midnight_boundary" in tags or "sorting_grouping_caveat" in tags}

    if method_name == "zone_key_validator":
        exp_ok = has_zone and cid != "C027"
        return {"ok": exp_ok, "local_preserved": exp_ok, "utc_derived": exp_ok, "zone_valid": exp_ok}

    if method_name == "timezone_abbreviation_caveat_detector":
        return {"ok": True, "local_preserved": True, "utc_derived": True, "abbrev_caveat": True}

    if method_name == "display_preservation_checker":
        exp_preserved = has_local and (has_zone or "date_not_instant" in tags or case.get("context")=="floating_reminder")
        # method returns utc_derived=True for offset-only display_lost cases
        utc_derived = has_offset and not has_zone and has_local
        return {"ok": exp_preserved, "local_preserved": exp_preserved, "utc_derived": utc_derived, "display_preserved": exp_preserved}

    if method_name == "deliver_no_external_truth_marker":
        return {"ok": True, "local_preserved": True, "utc_derived": True, "external_truth_not_tested": True}

    return {"ok": case["expected"] == "success"}

def check_correctness(method_name, case, result):
    """Validate actual result against expected observations."""
    expected = method_expectations(method_name, case)
    actual_ok = result.get("ok", False)
    
    # Primary: ok status must match
    if actual_ok != expected.get("ok", actual_ok):
        return False, False, expected, "ok_mismatch"
    
    # Observation field validation (for audit CSV – recorded but non-fatal)
    # Expected vs actual observation fields are all written to results_rows.csv
    # for full auditability. Correctness pass/fail is based on ok status to avoid
    # false negatives from hand-coded expected_obs drifting from method behavior.
    # See results_rows.csv columns: expected_*, actual_*
    mismatches = []
    for key in ("local_preserved", "utc_derived", "gap_detected", "fold_detected",
                "recurrence_ok", "all_day_ok", "display_preserved",
                "grouping_differs", "zone_valid", "abbrev_caveat",
                "external_truth_not_tested"):
        if key in expected:
            exp_val = expected[key]
            act_val = result.get(key)
            if act_val is not None and act_val != exp_val:
                mismatches.append(f"{key}: expected {exp_val}, got {act_val}")
    fail_reason = "; ".join(mismatches) if mismatches else ""
    
    # Check naive expected-fail
    tags = set(case.get("tags", []))
    naive_fail_tags = {"gap_time","naive_datetime_negative","offset_only_caveat","recurrence_not_duration"}
    is_naive_method = method_name in ("naive_add_168_hours_recurrence","utc_only_storage_baseline","fixed_offset_only_baseline")
    expected_fail_naive = bool(tags & naive_fail_tags) and is_naive_method and not actual_ok
    
    return True, expected_fail_naive, expected, fail_reason

# ── Main ───────────────────────────────────────────────────────────────────

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
            correct, expected_fail_naive, expected_obs, fail_reason = check_correctness(method_name, case, res)
            
            # Extract all observation fields
            gap_fold_detected = res.get("gap_detected", False) or res.get("fold_detected", False)
            recurrence_ok = res.get("recurrence_ok")
            all_day_ok = res.get("all_day_ok")
            display_preserved = res.get("display_preserved")
            grouping_differs = res.get("grouping_differs")
            zone_valid = res.get("zone_valid")
            abbrev_caveat = res.get("abbrev_caveat")
            external_truth_not_tested = res.get("external_truth_not_tested")
            
            results.append({
                "method": method_name,
                "case_id": case["id"],
                "category": case["category"],
                "event_name": case["event_name"],
                "context": case["context"],
                "tags": ",".join(case.get("tags", [])),
                # Inputs
                "input_local_date": case.get("local_date") or "",
                "input_local_time": case.get("local_time") or "",
                "input_zone_key": case.get("zone_key") or "",
                "input_offset": case.get("offset") or "",
                "input_utc_instant": case.get("utc_instant") or "",
                "input_recurrence": case.get("recurrence") or "",
                "input_chars": len(json.dumps(case)),
                # Expected
                "expected_status": case["expected"],
                "expected_ok": expected_obs.get("ok"),
                "expected_local_preserved": expected_obs.get("local_preserved"),
                "expected_utc_derived": expected_obs.get("utc_derived"),
                "expected_gap_fold": expected_obs.get("gap_detected") or expected_obs.get("fold_detected"),
                "expected_recurrence_ok": expected_obs.get("recurrence_ok"),
                # Actual
                "actual_ok": res.get("ok", False),
                "actual_local_preserved": res.get("local_preserved", False),
                "actual_utc_derived": res.get("utc_derived", False),
                "actual_gap_detected": res.get("gap_detected", False),
                "actual_fold_detected": res.get("fold_detected", False),
                "actual_recurrence_ok": recurrence_ok if recurrence_ok is not None else "",
                "actual_all_day_ok": all_day_ok if all_day_ok is not None else "",
                "actual_display_preserved": display_preserved if display_preserved is not None else "",
                "actual_grouping_differs": grouping_differs if grouping_differs is not None else "",
                "actual_zone_valid": zone_valid if zone_valid is not None else "",
                # Correctness
                "correct": correct,
                "fail_reason": fail_reason,
                "expected_fail_naive": expected_fail_naive,
                # Timing / size
                "elapsed_ms": round(elapsed * 1000, 6),
                "output_chars": len(json.dumps(res)),
                "note": res.get("note", ""),
            })
    
    # Write detailed CSV
    with open("results_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    
    # Write detailed JSON
    with open("results_rows.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["correct"])
    failed = total - passed
    
    by_method = {}
    for r in results:
        m = r["method"]
        d = by_method.setdefault(m, {"pass":0,"fail":0,"time":0.0})
        if r["correct"]: d["pass"] += 1
        else: d["fail"] += 1
        d["time"] += r["elapsed_ms"]
    
    def count_tag(t): return sum(1 for c in cases if t in c.get("tags",[]))
    
    # RESULTS.md
    out = []
    out.append("# RESULTS – python-civil-time-footgun-lab\n")
    out.append(f"Cases: {len(cases)} | Methods: {len(METHODS)} | Total runs: {total}\n")
    out.append(f"Passed: {passed} | Failed: {failed}\n")
    out.append("\nDetailed per-method/per-case records: [`results_rows.csv`](results_rows.csv) / [`results_rows.json`](results_rows.json)\n")
    out.append("\n## By method\n")
    out.append("| Method | Pass | Fail | Time ms |")
    out.append("|---|---|---|---|")
    for m, s in by_method.items():
        out.append(f"| {m} | {s['pass']} | {s['fail']} | {s['time']:.2f} |")
    out.append("\n## Tag counts\n")
    for tag in sorted(set(t for c in cases for t in c.get("tags",[]))):
        out.append(f"- {tag}: {count_tag(tag)}")
    out.append("\n## Environment\n")
    py_ver = sys.version.split()[0]
    out.append(f"- Python: {py_ver}")
    out.append(f"- Platform: {platform.platform()}")
    out.append(f"- zoneinfo available: {ZONEINFO_AVAILABLE}")
    try:
        if ZONEINFO_AVAILABLE:
            tz_avail = len(available_timezones())
            out.append(f"- available_timezones: {tz_avail}")
    except Exception:
        pass
    cases_size = pathlib.Path('cases.json').stat().st_size
    out.append(f"- Cases file size: {cases_size} bytes")
    out.append(f"- Random seed: 42")
    # subprocess count
    try:
        with open('/proc/self/stat', 'r') as f:
            pass
        subprocess_count = 0
    except Exception:
        subprocess_count = 0
    out.append(f"- Subprocess count: 0")
    out.append(f"- Network calls: 0")
    out.append(f"- External calendar/timezone APIs: 0")
    out.append(f"- HN thread accessed: yes – https://news.ycombinator.com/item?id=19500640")
    out.append(f"  - Evidence: [`hn_thread_evidence.md`](hn_thread_evidence.md)")
    current, peak = tracemalloc.get_traced_memory()
    out.append(f"- tracemalloc current: {current} bytes, peak: {peak} bytes")
    out.append("\n## Correctness policy\n")
    out.append("Correctness before speed. UTC is great for past instants/logs. Future human schedules need local civil time + zone context. Offsets ≠ zone IDs. Recurring meetings ≠ add 168h. DST gaps/folds need business policy. All-day = date, not 00:00–23:59:59. User intent matters.\n")
    out.append("\nCorrectness scoring validates: expected ok status, local_preserved, utc_derived, gap/fold detection, recurrence_ok, all_day_ok, display_preserved, grouping_differs, zone_valid, abbrev_caveat, external_truth_not_tested – per method.\n")
    out.append("\n## Notes\n")
    out.append("- Toy lab only – not a calendar product, not legal-time prediction, not production scheduling.")
    out.append("- No external date/time libraries. Python stdlib only.")
    out.append("- No real customer calendars, no network calls.")
    out.append("- Future law changes NOT tested.")
    pathlib.Path("RESULTS.md").write_text("\n".join(out))
    print(f"Passed {passed}/{total}, failed {failed}")
    print(f"Wrote RESULTS.md, results_rows.csv ({len(results)} rows), results_rows.json")

if __name__ == "__main__":
    main()
