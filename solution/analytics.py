
import csv
import json

from solution.database import get_connection


def get_call_statistics():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                link.lead_id,
                e.workflow_id,
                e.call_id,
                e.event_type,
                e.occurred_at,
                e.payload_json
            FROM events e
            JOIN event_lead_links link
                ON link.event_id = e.event_id
            WHERE e.call_id IS NOT NULL
            ORDER BY e.occurred_at
            """
        ).fetchall()

        calls = {}

        for row in rows:
            key = (row["lead_id"], row["call_id"])

            if key not in calls:
                calls[key] = {
                    "lead_id": row["lead_id"],
                    "workflow_id": row["workflow_id"],
                    "call_id": row["call_id"],
                    "initiated": False,
                    "connected": False,
                    "telephony_failed": False,
                    "initiated_at": None,
                    "dispositions": []
                }

            call = calls[key]

            if row["event_type"] == "call.initiated":
                call["initiated"] = True
                call["initiated_at"] = row["occurred_at"]

            elif row["event_type"] == "call.connected":
                call["connected"] = True

            elif row["event_type"] == "call.telephony_failed":
                call["telephony_failed"] = True

            elif row["event_type"] in (
                "disposition.set",
                "disposition.override"
            ):
                payload = json.loads(row["payload_json"])

                call["dispositions"].append({
                    "event_type": row["event_type"],
                    "occurred_at": row["occurred_at"],
                    "code": payload.get("disposition_code")
                })

        return [
            call for call in calls.values()
            if call["initiated"]
        ]

    finally:
        connection.close()


def load_disposition_details():
    dispositions = {}

    with open(
        "schemas/dispositions.csv",
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            key = (
                row["workflow_id"].strip(),
                row["code"].strip().lower()
            )

            dispositions[key] = {
                "is_terminal": row["is_terminal"].strip().lower() == "true",
                "is_success": row["is_success"].strip().lower() == "true"
            }

    return dispositions


def add_effective_dispositions(calls):
    disposition_details = load_disposition_details()

    for call in calls:
        events = call["dispositions"]

        overrides = [
            event for event in events
            if event["event_type"] == "disposition.override"
        ]

        if overrides:
            selected = max(
                overrides,
                key=lambda event: event["occurred_at"]
            )
        else:
            sets = [
                event for event in events
                if event["event_type"] == "disposition.set"
            ]

            selected = max(
                sets,
                key=lambda event: event["occurred_at"]
            ) if sets else None

        if selected is None:
            call["effective_disposition"] = None
            call["effective_disposition_at"] = None
            call["is_terminal"] = False
            call["is_success"] = False

        else:
            code = selected["code"]

            details = disposition_details.get(
                (call["workflow_id"], code),
                {}
            )

            call["effective_disposition"] = code
            call["effective_disposition_at"] = selected["occurred_at"]
            call["is_terminal"] = details.get("is_terminal", False)
            call["is_success"] = details.get("is_success", False)

    return calls


def calculate_lead_statistics(calls):
    """
    Combine all calls belonging to each lead
    and calculate the lead bucket.
    """

    connection = get_connection()

    try:
        lead_rows = connection.execute(
            """
            SELECT id, workflow_id
            FROM leads
            ORDER BY id
            """
        ).fetchall()

        leads = {}

        # Include every lead, even leads without calls.
        for row in lead_rows:
            leads[row["id"]] = {
                "lead_id": row["id"],
                "workflow_id": row["workflow_id"],
                "total_calls": 0,
                "connected_calls": 0,
                "all_calls_failed": True,
                "has_terminal": False,
                "ever_success": False,
                "last_call_at": None,
                "current_disposition": None,
                "current_disposition_at": None
            }

        # Combine call statistics for each lead.
        for call in calls:
            lead = leads.get(call["lead_id"])

            if lead is None:
                continue

            lead["total_calls"] += 1

            if call["connected"]:
                lead["connected_calls"] += 1

            if not call["telephony_failed"]:
                lead["all_calls_failed"] = False

            if call["is_terminal"]:
                lead["has_terminal"] = True

            if call["is_success"]:
                lead["ever_success"] = True

            initiated_at = call["initiated_at"]

            if (
                initiated_at
                and (
                    lead["last_call_at"] is None
                    or initiated_at > lead["last_call_at"]
                )
            ):
                lead["last_call_at"] = initiated_at

            disposition_at = call["effective_disposition_at"]

            if (
                call["effective_disposition"] is not None
                and (
                    lead["current_disposition_at"] is None
                    or disposition_at > lead["current_disposition_at"]
                )
            ):
                lead["current_disposition"] = call["effective_disposition"]
                lead["current_disposition_at"] = disposition_at

        # Assign one bucket to every lead.
        for lead in leads.values():

            if lead["total_calls"] == 0:
                lead["bucket"] = "yet_to_reach_out"

            elif lead["has_terminal"]:
                lead["bucket"] = "completed"

            elif lead["all_calls_failed"]:
                lead["bucket"] = "in_progress_telephony_failed"

            else:
                lead["bucket"] = "in_progress_dialed"

        return list(leads.values())

    finally:
        connection.close()


def print_lead_statistics(leads):
    print("Total leads:", len(leads))

    print("\nLead bucket summary:\n")

    bucket_counts = {}

    for lead in leads:
        bucket = lead["bucket"]
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    for bucket, count in sorted(bucket_counts.items()):
        print(bucket, ":", count)

    print("\nFirst five lead records:\n")

    for lead in leads[:5]:
        print("Lead ID:", lead["lead_id"])
        print("Workflow:", lead["workflow_id"])
        print("Total calls:", lead["total_calls"])
        print("Connected calls:", lead["connected_calls"])
        print("Bucket:", lead["bucket"])
        print("Current disposition:", lead["current_disposition"])
        print("Ever successful:", lead["ever_success"])
        print("Last call:", lead["last_call_at"])
        print("-" * 45)


if __name__ == "__main__":

    calls = get_call_statistics()

    calls = add_effective_dispositions(calls)

    leads = calculate_lead_statistics(calls)

    print_lead_statistics(leads)
