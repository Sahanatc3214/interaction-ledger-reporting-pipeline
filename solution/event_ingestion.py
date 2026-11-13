from pathlib import Path

from solution.event_processor import (
    read_event_file,
    validate_event,
    save_event,
    load_dispositions,
    validate_disposition_event
)


def find_event_files(data_folder="data"):
    """
    Find all event JSONL files in drop folders.
    """

    data_path = Path(data_folder)

    event_files = sorted(
        data_path.glob("drop_*/events/*.jsonl")
    )

    return event_files


def count_event_lines(file_path):
    """
    Count every non-empty line in an event file.
    """

    total = 0

    with open(file_path, "r", encoding="utf-8") as file:

        for line in file:

            if line.strip():
                total += 1

    return total


def process_event_file(file_path, allowed_dispositions):
    """
    Read, validate and save events from one JSONL file.
    """

    results = {
        "saved": 0,
        "malformed_events": 0,
        "duplicate_events_dropped": 0,
        "unknown_disposition_events": 0
    }

    # Identify the drop folder, such as drop_1 or drop_2.
    received_drop = Path(file_path).parent.parent.name

    # Read all non-empty event lines.
    events = read_event_file(file_path)

    # Process each event separately.
    for item in events:

        event = item["data"]

        # Step 1: Check for invalid JSON.
        if event is None:
            results["malformed_events"] += 1
            continue

        # Step 2: Validate the event structure.
        valid, reason = validate_event(event)

        if not valid:
            results["malformed_events"] += 1
            continue

        # Step 3: Validate disposition codes.
        valid, reason = validate_disposition_event(
            event,
            allowed_dispositions
        )

        if not valid:
            results["unknown_disposition_events"] += 1
            continue

        # Step 4: Save the event in SQLite.
        status = save_event(event, received_drop)

        if status == "saved":
            results["saved"] += 1

        elif status == "duplicate":
            results["duplicate_events_dropped"] += 1

        else:
            results["malformed_events"] += 1

    return results