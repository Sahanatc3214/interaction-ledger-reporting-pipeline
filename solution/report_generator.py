
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from solution.database import get_connection
from solution.security import decrypt_pii, mask_phone
from solution.analytics import (
    get_call_statistics,
    add_effective_dispositions,
    calculate_lead_statistics
)
from solution.lead_processor import validate_lead_file
from solution.event_processor import (
    validate_event,
    load_dispositions,
    validate_disposition_event
)


REPORT_FOLDER = Path("reports")
DATA_FOLDER = Path("data")
SCHEMA_FOLDER = Path("schemas")


# --------------------------------------------------
# 1. WRITE CSV REPORT
# --------------------------------------------------

def write_csv(file_name, headers, rows):

    REPORT_FOLDER.mkdir(exist_ok=True)

    file_path = REPORT_FOLDER / file_name

    with open(
        file_path,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=headers
        )

        writer.writeheader()
        writer.writerows(rows)

    print("Created:", file_path)


# --------------------------------------------------
# 2. GET LEAD DETAILS
# --------------------------------------------------

def get_lead_details():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                workflow_id,
                phone_encrypted,
                reference_value,
                batch_id
            FROM leads
            ORDER BY workflow_id, reference_value
            """
        ).fetchall()

        leads = []

        for row in rows:

            phone = decrypt_pii(
                row["phone_encrypted"]
            )

            leads.append({
                "lead_id": row["id"],
                "workflow_id": row["workflow_id"],
                "external_ref": row["reference_value"],
                "batch_id": row["batch_id"],
                "phone_masked": mask_phone(phone)
            })

        return leads

    finally:
        connection.close()


# --------------------------------------------------
# 3. BATCH SUMMARY REPORT
# --------------------------------------------------

def generate_batch_summary(leads):

    grouped = defaultdict(list)

    for lead in leads:

        key = (
            lead["workflow_id"],
            lead["batch_id"]
        )

        grouped[key].append(lead)

    rows = []

    for (workflow_id, batch_id), batch_leads in sorted(grouped.items()):

        counts = {
            "yet_to_reach_out": 0,
            "in_progress_telephony_failed": 0,
            "in_progress_dialed": 0,
            "completed": 0
        }

        for lead in batch_leads:

            bucket = lead["bucket"]
            counts[bucket] += 1

        rows.append({

            "workflow_id": workflow_id,
            "batch_id": batch_id,
            "total_leads": len(batch_leads),

            "yet_to_reach_out":
                counts["yet_to_reach_out"],

            "in_progress_telephony_failed":
                counts["in_progress_telephony_failed"],

            "in_progress_dialed":
                counts["in_progress_dialed"],

            "completed":
                counts["completed"]
        })

    write_csv(
        "batch_summary.csv",
        [
            "workflow_id",
            "batch_id",
            "total_leads",
            "yet_to_reach_out",
            "in_progress_telephony_failed",
            "in_progress_dialed",
            "completed"
        ],
        rows
    )


# --------------------------------------------------
# 4. DAILY OVERVIEW REPORT
# --------------------------------------------------

def generate_daily_overview(calls):

    grouped = defaultdict(list)

    for call in calls:

        initiated_at = datetime.fromisoformat(
            call["initiated_at"]
        )

        call_date = initiated_at.date().isoformat()

        key = (
            call["workflow_id"],
            call_date
        )

        grouped[key].append(call)

    rows = []

    for (workflow_id, call_date), daily_calls in sorted(grouped.items()):

        total_calls = len(daily_calls)

        connected_calls = sum(
            1
            for call in daily_calls
            if call["connected"]
        )

        success_leads = {
            call["lead_id"]
            for call in daily_calls
            if call["is_success"]
        }

        connectivity_rate = (
            connected_calls / total_calls
        )

        rows.append({

            "workflow_id": workflow_id,
            "date": call_date,
            "total_calls": total_calls,
            "connected_calls": connected_calls,

            "connectivity_rate":
                f"{connectivity_rate:.4f}",

            "success_leads": len(success_leads)
        })

    write_csv(
        "daily_overview.csv",
        [
            "workflow_id",
            "date",
            "total_calls",
            "connected_calls",
            "connectivity_rate",
            "success_leads"
        ],
        rows
    )


# --------------------------------------------------
# 5. LEAD REPORT
# --------------------------------------------------

def generate_lead_report(leads, calls, lead_statistics):

    stats_by_id = {
        lead["lead_id"]: lead
        for lead in lead_statistics
    }

    calls_by_lead = defaultdict(list)

    for call in calls:
        calls_by_lead[call["lead_id"]].append(call)

    rows = []

    for lead in leads:

        lead_id = lead["lead_id"]

        stats = stats_by_id[lead_id]

        lead_calls = calls_by_lead[lead_id]

        calls_with_disposition = [
            call
            for call in lead_calls
            if call["effective_disposition"] is not None
        ]

        # Current disposition belongs to the most recent
        # initiated call that has an effective disposition.

        latest_disposition_call = None

        if calls_with_disposition:

            latest_disposition_call = max(
                calls_with_disposition,
                key=lambda call: call["initiated_at"]
            )

        current_disposition = (
            latest_disposition_call["effective_disposition"]
            if latest_disposition_call
            else ""
        )

        rows.append({

            "workflow_id": lead["workflow_id"],
            "external_ref": lead["external_ref"],
            "batch_id": lead["batch_id"],
            "phone_masked": lead["phone_masked"],

            "bucket": stats["bucket"],
            "total_calls": stats["total_calls"],
            "connected_calls": stats["connected_calls"],

            "last_call_at":
                stats["last_call_at"] or "",

            "current_disposition":
                current_disposition,

            "ever_success":
                str(stats["ever_success"]).lower()
        })

    rows.sort(
        key=lambda row: (
            row["workflow_id"],
            row["external_ref"]
        )
    )

    write_csv(
        "lead_report.csv",
        [
            "workflow_id",
            "external_ref",
            "batch_id",
            "phone_masked",
            "bucket",
            "total_calls",
            "connected_calls",
            "last_call_at",
            "current_disposition",
            "ever_success"
        ],
        rows
    )


# --------------------------------------------------
# 6. REJECTIONS REPORT
# --------------------------------------------------

def generate_rejections_report():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                workflow_id,
                batch_id,
                row_number,
                reason
            FROM rejections
            ORDER BY
                workflow_id,
                batch_id,
                row_number
            """
        ).fetchall()

        report_rows = [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()

    write_csv(
        "rejections.csv",
        [
            "workflow_id",
            "batch_id",
            "row_number",
            "reason"
        ],
        report_rows
    )


# --------------------------------------------------
# 7. DATA QUALITY REPORT
# --------------------------------------------------

def generate_data_quality():

    # Load workflow schemas.

    schemas = {}

    for schema_file in SCHEMA_FOLDER.glob("*.json"):

        with open(
            schema_file,
            "r",
            encoding="utf-8"
        ) as file:

            schema = json.load(file)

        schemas[schema["workflow_id"]] = schema

    # Calculate lead statistics from original CSV files.

    lead_rows_total = 0
    lead_rows_rejected = 0
    duplicate_lead_rows_merged = 0
    field_warnings = 0

    rejections_by_reason = {}

    seen_leads = set()

    lead_files = sorted(
        DATA_FOLDER.glob("drop_*/leads/*/*.csv")
    )

    for csv_file in lead_files:

        workflow_id = csv_file.parent.name

        schema = schemas[workflow_id]

        result = validate_lead_file(
            csv_file,
            schema
        )

        lead_rows_total += result["total_rows"]

        lead_rows_rejected += len(
            result["rejected"]
        )

        field_warnings += result["field_warnings"]

        for rejected in result["rejected"]:

            reason = rejected["reason"]

            rejections_by_reason[reason] = (
                rejections_by_reason.get(reason, 0) + 1
            )

        for record in result["accepted"]:

            phone = record["data"]["phone"]

            identity = (
                workflow_id,
                phone
            )

            if identity in seen_leads:

                duplicate_lead_rows_merged += 1

            else:

                seen_leads.add(identity)

    # Calculate event statistics from original JSONL files.

    events_total = 0
    malformed_events = 0
    duplicate_events_dropped = 0
    unknown_disposition_events = 0

    seen_event_ids = set()

    allowed_dispositions = load_dispositions()

    event_files = sorted(
        DATA_FOLDER.glob("drop_*/events/*.jsonl")
    )

    for event_file in event_files:

        with open(
            event_file,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                if not line.strip():
                    continue

                events_total += 1

                try:

                    event = json.loads(line)

                except json.JSONDecodeError:

                    malformed_events += 1
                    continue

                valid, reason = validate_event(event)

                if not valid:

                    malformed_events += 1
                    continue

                event_id = event["event_id"]

                if event_id in seen_event_ids:

                    duplicate_events_dropped += 1
                    continue

                seen_event_ids.add(event_id)

                valid, reason = validate_disposition_event(
                    event,
                    allowed_dispositions
                )

                if not valid:

                    unknown_disposition_events += 1

    # Read final orphan count from database.

    connection = get_connection()

    try:

        orphan_events = connection.execute(
            """
            SELECT COUNT(*)
            FROM event_quarantine
            """
        ).fetchone()[0]

    finally:
        connection.close()

    # Prepare final JSON.

    quality = {

        "lead_rows_total":
            lead_rows_total,

        "lead_rows_rejected":
            lead_rows_rejected,

        "rejections_by_reason":
            dict(sorted(rejections_by_reason.items())),

        "duplicate_lead_rows_merged":
            duplicate_lead_rows_merged,

        "field_warnings":
            field_warnings,

        "events_total":
            events_total,

        "malformed_events":
            malformed_events,

        "duplicate_events_dropped":
            duplicate_events_dropped,

        "orphan_events":
            orphan_events,

        "unknown_disposition_events":
            unknown_disposition_events
    }

    REPORT_FOLDER.mkdir(exist_ok=True)

    file_path = REPORT_FOLDER / "data_quality.json"

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            quality,
            file,
            indent=4
        )

    print("Created:", file_path)

    print("\nData quality statistics:\n")

    print(json.dumps(quality, indent=4))


# --------------------------------------------------
# 8. GENERATE ALL FIVE REPORTS
# --------------------------------------------------

def generate_reports():

    print("\nGenerating reports...\n")

    # Rebuild call statistics.

    calls = get_call_statistics()

    calls = add_effective_dispositions(calls)

    # Calculate lead statistics.

    lead_statistics = calculate_lead_statistics(calls)

    leads = get_lead_details()

    # Add bucket information to each lead.

    stats_by_id = {
        lead["lead_id"]: lead
        for lead in lead_statistics
    }

    for lead in leads:

        stats = stats_by_id[lead["lead_id"]]

        lead["bucket"] = stats["bucket"]

    # Generate all reports.

    generate_batch_summary(leads)

    generate_daily_overview(calls)

    generate_lead_report(
        leads,
        calls,
        lead_statistics
    )

    generate_rejections_report()

    generate_data_quality()

    print("\nAll five reports generated successfully!")


# --------------------------------------------------
# 9. MAIN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":

    generate_reports()
