#!/usr/bin/env python3
"""Generate deterministic civil-time / scheduling footgun cases."""
import json
import random
from pathlib import Path

random.seed(42)

CASES = [
    # past log event – UTC is appropriate
    {"id":"C001","category":"past_instant","event_name":"Example Server Log Entry","local_date":None,"local_time":None,"zone_key":"UTC","offset":None,"utc_instant":"2023-06-15T14:30:00+00:00","recurrence":"one_time_event","context":"past_log_instant","tags":["utc_good_for_past_instant","aware_datetime"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # future one-time local event
    {"id":"C002","category":"future_local","event_name":"Example Standup","local_date":"2026-10-05","local_time":"09:30:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["future_local_intent","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # future event stored UTC-only – loses intent
    {"id":"C003","category":"future_utc_only","event_name":"Test Conference","local_date":"2026-11-12","local_time":"10:00:00","zone_key":"Europe/Paris","offset":None,"utc_instant":"2026-11-12T09:00:00+00:00","recurrence":"one_time_event","context":"future_human_schedule","tags":["utc_only_loses_context"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # future event with local+zone preserved
    {"id":"C004","category":"future_local_preserved","event_name":"Fictional Backup Window","local_date":"2026-09-20","local_time":"02:00:00","zone_key":"America/Los_Angeles","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["future_local_intent","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # offset-only – lossy
    {"id":"C005","category":"offset_only","event_name":"Toy Store Opening","local_date":"2026-08-15","local_time":"11:00:00","zone_key":None,"offset":"-05:00","utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["offset_only_caveat","fixed_offset_caveat"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # weekly meeting across spring DST
    {"id":"C006","category":"recurring_dst_spring","event_name":"Demo Office Hours","local_date":"2026-03-09","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"weekly_same_local_time","context":"recurring_meeting","tags":["weekly_dst","recurrence_not_duration"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # weekly meeting across fall DST
    {"id":"C007","category":"recurring_dst_fall","event_name":"Synthetic Reminder","local_date":"2026-11-02","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"weekly_same_local_time","context":"recurring_meeting","tags":["weekly_dst","recurrence_not_duration","fold_time"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"fold_time"},
    # 7 calendar days vs 168 hours
    {"id":"C008","category":"recurrence_duration_vs_calendar","event_name":"Example Standup","local_date":"2026-03-09","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"weekly_same_local_time","context":"recurring_meeting","tags":["recurrence_not_duration"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # gap time – spring forward
    {"id":"C009","category":"dst_gap","event_name":"Test Conference","local_date":"2026-03-08","local_time":"02:30:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["gap_time","fold_policy_needed","business_rule_needed"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"gap_time"},
    # fold time – fall back
    {"id":"C010","category":"dst_fold","event_name":"Fictional Backup Window","local_date":"2026-11-01","local_time":"01:30:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["fold_time","fold_policy_needed","business_rule_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"fold_time"},
    # fold=0 vs fold=1 ambiguity
    {"id":"C011","category":"dst_fold_ambig","event_name":"Toy Store Opening","local_date":"2026-11-01","local_time":"01:15:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["fold_time","fold_policy_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"fold_time"},
    # all-day event – date only
    {"id":"C012","category":"all_day_date","event_name":"Demo Office Hours","local_date":"2026-07-04","local_time":None,"zone_key":None,"offset":None,"utc_instant":None,"recurrence":"all_day_date","context":"all_day_event","tags":["all_day_date","date_not_instant"],"expected":"success","local_display_preserved":True,"utc_derived":False,"gap_fold":"not_applicable"},
    # bad all-day 00:00–23:59:59
    {"id":"C013","category":"all_day_bad_range","event_name":"Synthetic Reminder","local_date":"2026-07-04","local_time":"00:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"all_day_date","context":"all_day_event","tags":["bad_end_of_day","date_not_instant"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"not_applicable"},
    # birthday / date-only
    {"id":"C014","category":"birthday_date_only","event_name":"Example Birthday","local_date":"1990-05-15","local_time":None,"zone_key":None,"offset":None,"utc_instant":None,"recurrence":"all_day_date","context":"all_day_event","tags":["date_not_instant","all_day_date"],"expected":"success","local_display_preserved":True,"utc_derived":False,"gap_fold":"not_applicable"},
    # midnight boundary UTC vs local
    {"id":"C015","category":"midnight_boundary","event_name":"Example Standup","local_date":"2026-06-01","local_time":"00:15:00","zone_key":"Asia/Tokyo","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"display_grouping","tags":["midnight_boundary","sorting_grouping_caveat"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # lunch time local interpretation
    {"id":"C016","category":"lunch_local","event_name":"Test Conference","local_date":"2026-06-10","local_time":"12:00:00","zone_key":"Europe/Paris","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["future_local_intent","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # global webinar with explicit coord zone
    {"id":"C017","category":"global_webinar","event_name":"Fictional Webinar","local_date":"2026-09-01","local_time":"15:00:00","zone_key":"UTC","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["zone_id_preserved","aware_datetime"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # floating personal reminder
    {"id":"C018","category":"floating_reminder","event_name":"Toy Reminder","local_date":"2026-08-20","local_time":"07:00:00","zone_key":None,"offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"floating_reminder","tags":["future_local_intent","business_rule_needed"],"expected":"success","local_display_preserved":True,"utc_derived":False,"gap_fold":"not_applicable"},
    # travel reminder caveat
    {"id":"C019","category":"travel_reminder","event_name":"Demo Office Hours","local_date":"2026-10-10","local_time":"07:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"travel_caveat","tags":["future_local_intent","business_rule_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # backup job during DST gap
    {"id":"C020","category":"backup_gap","event_name":"Fictional Backup Window","local_date":"2026-03-08","local_time":"02:15:00","zone_key":"America/Los_Angeles","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"backup_job","tags":["gap_time","fold_policy_needed","business_rule_needed"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"gap_time"},
    # maintenance during DST fold
    {"id":"C021","category":"maintenance_fold","event_name":"Synthetic Reminder","local_date":"2026-11-01","local_time":"01:45:00","zone_key":"America/Los_Angeles","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"backup_job","tags":["fold_time","fold_policy_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"fold_time"},
    # half-hour offset zone
    {"id":"C022","category":"half_hour_offset","event_name":"Example Standup","local_date":"2026-06-15","local_time":"14:00:00","zone_key":"Asia/Kolkata","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["non_hour_offset","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # quarter-hour offset if available
    {"id":"C023","category":"quarter_hour_offset","event_name":"Test Conference","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"Asia/Kathmandu","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["non_hour_offset","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # Lord Howe unusual DST
    {"id":"C024","category":"lord_howe","event_name":"Fictional Backup Window","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"Australia/Lord_Howe","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["non_hour_offset","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # historical dateline caveat
    {"id":"C025","category":"dateline_caveat","event_name":"Toy Store Opening","local_date":"2026-06-15","local_time":"12:00:00","zone_key":"Pacific/Apia","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["zone_id_preserved","business_rule_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # fixed-offset case
    {"id":"C026","category":"fixed_offset","event_name":"Demo Office Hours","local_date":"2026-06-15","local_time":"10:00:00","zone_key":None,"offset":"+02:00","utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["fixed_offset_caveat","offset_only_caveat"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # invalid zone key
    {"id":"C027","category":"invalid_zone","event_name":"Synthetic Reminder","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"Fake/Nowhere","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"invalid_input","tags":["invalid_zone"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"not_applicable"},
    # naive datetime negative
    {"id":"C028","category":"naive_negative","event_name":"Example Standup","local_date":"2026-06-15","local_time":"10:00:00","zone_key":None,"offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"invalid_input","tags":["naive_datetime_negative"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"not_applicable"},
    # aware datetime positive
    {"id":"C029","category":"aware_positive","event_name":"Test Conference","local_date":"2025-12-01","local_time":"15:00:00","zone_key":"UTC","offset":None,"utc_instant":"2025-12-01T15:00:00+00:00","recurrence":"one_time_event","context":"past_log_instant","tags":["aware_datetime","utc_good_for_past_instant"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # tz-aware round trip
    {"id":"C030","category":"round_trip","event_name":"Fictional Backup Window","local_date":"2024-01-15","local_time":"12:00:00","zone_key":"Europe/Paris","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"past_log_instant","tags":["aware_datetime","utc_good_for_past_instant","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # local-to-UTC with gap/fold policy
    {"id":"C031","category":"local_to_utc_policy","event_name":"Toy Store Opening","local_date":"2026-11-01","local_time":"01:30:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["fold_time","fold_policy_needed","business_rule_needed"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"fold_time"},
    # recurring UTC instants move, local stable
    {"id":"C032","category":"recurring_local_stable","event_name":"Demo Office Hours","local_date":"2026-02-15","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"weekly_same_local_time","context":"recurring_meeting","tags":["recurrence_not_duration","weekly_dst"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # recurring local moves if naive duration
    {"id":"C033","category":"recurring_naive_drift","event_name":"Synthetic Reminder","local_date":"2026-02-15","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"add_168_hours","context":"recurring_meeting","tags":["recurrence_not_duration"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # sorting UTC vs local date
    {"id":"C034","category":"sorting_grouping","event_name":"Example Standup","local_date":"2026-06-01","local_time":"23:30:00","zone_key":"Asia/Tokyo","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"display_grouping","tags":["sorting_grouping_caveat","midnight_boundary"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # same day differs by viewer TZ
    {"id":"C035","category":"same_day_viewer","event_name":"Test Conference","local_date":"2026-06-01","local_time":"01:00:00","zone_key":"America/Los_Angeles","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"display_grouping","tags":["sorting_grouping_caveat"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # end of month recurrence
    {"id":"C036","category":"eom_recurrence","event_name":"Fictional Backup Window","local_date":"2026-01-31","local_time":"10:00:00","zone_key":"UTC","offset":None,"utc_instant":None,"recurrence":"month_end_caveat","context":"recurring_meeting","tags":["month_length_caveat","recurrence_not_duration"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # leap year Feb 29
    {"id":"C037","category":"leap_year","event_name":"Toy Store Opening","local_date":"2028-02-29","local_time":"12:00:00","zone_key":"UTC","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["leap_year_caveat","date_not_instant"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # month length caveat
    {"id":"C038","category":"month_length","event_name":"Demo Office Hours","local_date":"2026-01-31","local_time":"10:00:00","zone_key":"UTC","offset":None,"utc_instant":None,"recurrence":"month_end_caveat","context":"recurring_meeting","tags":["month_length_caveat","recurrence_not_duration"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # TZ abbreviation ambiguous CST
    {"id":"C039","category":"tz_abbrev_ambiguous","event_name":"Synthetic Reminder","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"America/Chicago","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["timezone_abbreviation_caveat","display_loss"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # ISO offset string loses zone name
    {"id":"C040","category":"iso_offset_loses_zone","event_name":"Example Standup","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"America/New_York","offset":"-04:00","utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["offset_only_caveat","display_loss"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # display formatting loses TZ label
    {"id":"C041","category":"display_loss","event_name":"Test Conference","local_date":"2026-06-15","local_time":"10:00:00","zone_key":"Europe/Paris","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"display_grouping","tags":["display_loss"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # user-entered local preserved even if UTC changes
    {"id":"C042","category":"local_preserved_utc_moves","event_name":"Fictional Backup Window","local_date":"2026-10-15","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["future_local_intent","zone_id_preserved"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # derived UTC useful for ordering not authoritative
    {"id":"C043","category":"utc_ordering_not_authority","event_name":"Toy Store Opening","local_date":"2026-09-10","local_time":"14:00:00","zone_key":"Europe/Paris","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"display_grouping","tags":["sorting_grouping_caveat","future_local_intent"],"expected":"success","local_display_preserved":True,"utc_derived":True,"gap_fold":"not_applicable"},
    # business rules decide skipped/ambiguous
    {"id":"C044","category":"business_rule_skipped","event_name":"Demo Office Hours","local_date":"2026-03-08","local_time":"02:30:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["gap_time","business_rule_needed","fold_policy_needed"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"gap_time"},
    # naive method should fail – gap
    {"id":"C045","category":"naive_fail_gap","event_name":"Synthetic Reminder","local_date":"2026-03-08","local_time":"02:20:00","zone_key":"America/Chicago","offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["gap_time","business_rule_needed"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"gap_time"},
    # naive method should fail – naive datetime
    {"id":"C046","category":"naive_fail_naive_dt","event_name":"Example Standup","local_date":"2026-06-15","local_time":"10:00:00","zone_key":None,"offset":None,"utc_instant":None,"recurrence":"one_time_event","context":"invalid_input","tags":["naive_datetime_negative"],"expected":"error","local_display_preserved":False,"utc_derived":False,"gap_fold":"not_applicable"},
    # naive method should fail – offset as zone
    {"id":"C047","category":"naive_fail_offset_zone","event_name":"Test Conference","local_date":"2026-06-15","local_time":"10:00:00","zone_key":None,"offset":"-05:00","utc_instant":None,"recurrence":"one_time_event","context":"future_human_schedule","tags":["offset_only_caveat","fixed_offset_caveat"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
    # naive method should fail – 168h recurrence
    {"id":"C048","category":"naive_fail_168h","event_name":"Fictional Backup Window","local_date":"2026-03-09","local_time":"09:00:00","zone_key":"America/New_York","offset":None,"utc_instant":None,"recurrence":"add_168_hours","context":"recurring_meeting","tags":["recurrence_not_duration"],"expected":"success","local_display_preserved":False,"utc_derived":True,"gap_fold":"not_applicable"},
]

def main():
    out = Path("cases.json")
    out.write_text(json.dumps(CASES, indent=2))
    print(f"Wrote {len(CASES)} cases to {out}")

if __name__ == "__main__":
    main()
