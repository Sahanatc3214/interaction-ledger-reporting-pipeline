
import csv
import json
from datetime import datetime, timezone, timedelta

from solution.database import get_connection
from solution.security import encrypt_pii, phone_lookup_hash
from solution.validators import normalize_phone


def read_event_file(file_path):
    """
    Read events from a JSONL file.
    Each non-empty line represents one event.
    """

    events = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                continue

            try:
                event = json.loads(line)

                events.append({
                    "line_number": line_number,
                    "data": event
                })

            except json.JSONDecodeError:
                events.append({
                    "line_number": line_number,
                    "data": None
                })

    return events


def validate_event(event):
    """
    Validate the basic event structure.
    """

    if not isinstance(event, dict):
        return False, "invalid_event"

    if not event.get("event_id"):
        return False, "missing_event_id"

    if not event.get("event_type"):
        return False, "missing_event_type"

    if not event.get("workflow_id"):
        return False, "missing_workflow_id"

    return True, None


def event_already_exists(event_id):
    """
    Check whether an event ID already exists in SQLite.
    """

    connection = get_connection()

    try:
        result = connection.execute(
            """
            SELECT 1
            FROM events
            WHERE event_id = ?
            """,
            (event_id,)
        ).fetchone()

        return result is not None

    finally:
        connection.close()


def normalize_event_timestamp(value):
    """
    Convert an event timestamp into IST.

    Supported:
    1. UTC timestamps ending in Z
    2. Timestamps with timezone offsets
    3. Naive timestamps treated as IST
    """

    if not value:
        return None

    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    parsed = datetime.fromisoformat(value)

    ist = timezone(timedelta(hours=5, minutes=30))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ist)

    parsed = parsed.astimezone(ist)

    return parsed.isoformat()


def save_event(event, received_drop):
    """
    Save one valid event securely into SQLite.
    Store timestamps in IST.
    """

    valid, reason = validate_event(event)

    if not valid:
        return "invalid_event"

    connection = get_connection()

    try:
        # Step 1: Check duplicate event ID
        existing = connection.execute(
            """
            SELECT 1
            FROM events
            WHERE event_id = ?
            """,
            (event["event_id"],)
        ).fetchone()

        if existing:
            return "duplicate"

        # Step 2: Normalize phone and generate lookup hash
        phone = event.get("phone")
        phone_hash = None

        if phone:
            try:
                normalized_phone = normalize_phone(phone)
                phone_hash = phone_lookup_hash(normalized_phone)
            except ValueError:
                phone_hash = None

        # Step 3: Encrypt the complete raw event
        encrypted_raw = encrypt_pii(
            json.dumps(event)
        )

        # Step 4: Normalize timestamp into IST
        normalized_timestamp = normalize_event_timestamp(
            event.get("occurred_at")
        )

        # Step 5: Read event payload
        payload = event.get("payload", {})

        if not isinstance(payload, dict):
            payload = {}

        # Step 6: Insert event into database
        connection.execute(
            """
            INSERT INTO events (
                event_id,
                event_type,
                workflow_id,
                call_id,
                occurred_at,
                phone_hash,
                payload_json,
                raw_event_encrypted,
                received_drop
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["event_type"],
                event["workflow_id"],
                event.get("call_id"),
                normalized_timestamp,
                phone_hash,
                json.dumps(payload),
                encrypted_raw,
                received_drop
            )
        )

        connection.commit()

        return "saved"

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def load_dispositions(file_path="schemas/dispositions.csv"):
    """
    Load allowed disposition codes for each workflow.
    """

    dispositions = {}

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            workflow_id = row["workflow_id"].strip()
            code = row["code"].strip().lower()

            dispositions.setdefault(
                workflow_id, set()
            ).add(code)

    return dispositions


def validate_disposition_event(event, allowed_dispositions):
    """
    Validate disposition codes for the workflow.
    """

    event_type = event.get("event_type")

    if event_type not in (
        "disposition.set",
        "disposition.override"
    ):
        return True, None

    payload = event.get("payload") or {}

    if not isinstance(payload, dict):
        return False, "unknown_disposition"

    code = payload.get("disposition_code")

    if not isinstance(code, str):
        return False, "unknown_disposition"

    code = code.strip().lower()

    workflow_id = event.get("workflow_id")

    allowed_codes = allowed_dispositions.get(
        workflow_id, set()
    )

    if code not in allowed_codes:
        return False, "unknown_disposition"

    return True, None
