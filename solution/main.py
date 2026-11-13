
import json
from pathlib import Path

from solution.database import initialize_database
from solution.lead_processor import save_lead_file
from solution.event_ingestion import (
    find_event_files,
    process_event_file,
)
from solution.event_processor import load_dispositions
from solution.event_linker import link_events_to_leads
from solution.report_generator import generate_reports


def load_schemas(schema_folder="schemas"):
    """Load all workflow schemas."""

    schemas = {}

    for schema_file in Path(schema_folder).glob("*.json"):
        with open(schema_file, "r", encoding="utf-8") as file:
            schema = json.load(file)

        schemas[schema["workflow_id"]] = schema

    return schemas


def ingest_leads(data_folder, schemas):
    """Process all lead CSV files."""

    print("\nSTEP 1: INGESTING LEAD FILES")

    lead_files = sorted(
        Path(data_folder).glob("drop_*/leads/*/*.csv")
    )

    for csv_file in lead_files:
        workflow_id = csv_file.parent.name
        schema = schemas[workflow_id]

        result = save_lead_file(csv_file, schema)

        print(
            csv_file.name,
            "->",
            result["status"],
            "| Accepted:",
            result["accepted"],
            "| Rejected:",
            result["rejected"]
        )


def ingest_events(data_folder):
    """Process all event JSONL files."""

    print("\nSTEP 2: INGESTING EVENT FILES")

    allowed_dispositions = load_dispositions()

    event_files = find_event_files(data_folder)

    for event_file in event_files:
        result = process_event_file(
            event_file,
            allowed_dispositions
        )

        print(
            event_file.name,
            "-> Saved:",
            result["saved"],
            "| Duplicates:",
            result["duplicate_events_dropped"],
            "| Malformed:",
            result["malformed_events"],
            "| Unknown dispositions:",
            result["unknown_disposition_events"]
        )


def main():

    print("=" * 55)
    print("INTERACTION LEDGER AND REPORTING PIPELINE")
    print("=" * 55)

    data_folder = "data"

    # Initialize the database.
    print("\nInitializing database...")
    initialize_database()

    # Load workflow schemas.
    schemas = load_schemas()

    print("Loaded workflows:", list(schemas.keys()))

    # Process leads first.
    ingest_leads(data_folder, schemas)

    # Process events.
    ingest_events(data_folder)

    # Link events to leads.
    print("\nSTEP 3: LINKING EVENTS TO LEADS")

    link_results = link_events_to_leads()

    print("Directly linked:", link_results["directly_linked"])
    print("Override linked:", link_results["override_linked"])
    print("Orphaned:", link_results["orphaned"])

    # Generate all five reports.
    print("\nSTEP 4: GENERATING REPORTS")

    generate_reports()

    print("\n" + "=" * 55)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 55)


if __name__ == "__main__":
    main()
