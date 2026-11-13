from solution.validators import normalize_value
import re
import csv
import json
import hashlib
from pathlib import Path

from solution.database import get_connection
from solution.security import encrypt_pii, phone_lookup_hash


def normalize_header(header):
    """
    Convert CSV headers into a standard format.
    """
    header = str(header).strip().lower()
    header = re.sub(r"[_\s]+", " ", header)
    return header


def create_header_mapping(csv_headers, schema):
    """
    Match CSV headers with schema field names and aliases.
    """

    mapping = {}

    for field in schema["fields"]:

        possible_names = [field["name"]] + field.get("aliases", [])

        normalized_names = {
            normalize_header(name)
            for name in possible_names
        }

        for csv_header in csv_headers:

            normalized_csv_header = normalize_header(csv_header)

            if normalized_csv_header in normalized_names:
                mapping[field["name"]] = csv_header
                break

    return mapping


def read_lead_csv(csv_path, schema):
    """
    Read CSV records and map columns to schema fields.
    """

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:

        reader = csv.DictReader(file)

        csv_headers = reader.fieldnames or []

        header_mapping = create_header_mapping(
            csv_headers,
            schema
        )

        rows = []
        row_number = 0

        for row in reader:

            # Skip completely blank rows
            if not any(
                str(value or "").strip()
                for value in row.values()
            ):
                continue

            row_number += 1

            normalized_row = {}

            for schema_field, csv_column in header_mapping.items():
                normalized_row[schema_field] = row.get(csv_column)

            rows.append({
                "row_number": row_number,
                "data": normalized_row
            })

        return rows

def validate_lead_row(row_data, schema):
    """
    Validate and normalize one customer record.
    """

    normalized_data = {}
    warnings = 0

    # Process fields in schema order
    for field in schema["fields"]:

        field_name = field["name"]
        raw_value = row_data.get(field_name)

        # Check missing values
        if raw_value is None or str(raw_value).strip() == "":

            if field["required"]:
                return None, f"missing_required:{field_name}", warnings

            normalized_data[field_name] = None
            continue

        # Normalize the field value
        try:
            normalized_data[field_name] = normalize_value(
                raw_value,
                field
            )

        except ValueError as error:

            # Invalid required field: reject the record
            if field["required"]:

                if field["type"] == "phone":
                    return None, "invalid_phone", warnings

                return None, str(error), warnings

            # Invalid optional field: keep record, add warning
            normalized_data[field_name] = None
            warnings += 1

    return normalized_data, None, warnings

def validate_lead_file(csv_path, schema):
    """
    Validate every customer record in a CSV file.
    """

    rows = read_lead_csv(csv_path, schema)

    accepted_records = []
    rejected_records = []

    total_warnings = 0

    for row in rows:

        normalized_data, reason, warnings = validate_lead_row(
            row["data"],
            schema
        )

        total_warnings += warnings

        if reason is not None:

            rejected_records.append({
                "row_number": row["row_number"],
                "reason": reason
            })

        else:

            accepted_records.append({
                "row_number": row["row_number"],
                "data": normalized_data
            })

    return {
        "total_rows": len(rows),
        "accepted": accepted_records,
        "rejected": rejected_records,
        "field_warnings": total_warnings
    }

def save_lead_file(csv_path, schema):
    """
    Validate a CSV file and save accepted leads securely.
    Save rejected records separately.
    """

    csv_path = Path(csv_path)
    workflow_id = schema["workflow_id"]
    batch_id = csv_path.stem

    result = validate_lead_file(csv_path, schema)

    file_hash = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()

    file_path = str(csv_path.resolve())

    connection = get_connection()

    try:
        # Prevent processing the same file twice
        existing_file = connection.execute(
            "SELECT id FROM ingested_files WHERE file_path = ?",
            (file_path,)
        ).fetchone()

        if existing_file:
            return {
                "status": "already_ingested",
                "total_rows": 0,
                "accepted": 0,
                "rejected": 0,
                "duplicates_merged": 0,
                "field_warnings": 0
            }

        duplicates_merged = 0

        for record in result["accepted"]:

            data = record["data"]

            phone = data["phone"]
            customer_name = data["customer_name"]

            phone_hash = phone_lookup_hash(phone)
            encrypted_phone = encrypt_pii(phone)
            encrypted_name = encrypt_pii(customer_name)

            # Find the reference field, such as policy_number
            reference_field = next(
                field["name"]
                for field in schema["fields"]
                if field.get("reference")
            )

            reference_value = data[reference_field]

            # Keep only non-PII fields in fields_json
            non_pii_fields = {
                field["name"]
                for field in schema["fields"]
                if not field.get("pii", False)
                and field["name"] != reference_field
            }

            fields = {
                key: data[key]
                for key in non_pii_fields
            }

            existing_lead = connection.execute(
                """
                SELECT id, fields_json
                FROM leads
                WHERE workflow_id = ? AND phone_hash = ?
                """,
                (workflow_id, phone_hash)
            ).fetchone()

            if existing_lead:

                # Merge only non-null incoming values
                old_fields = json.loads(
                    existing_lead["fields_json"]
                )

                for key, value in fields.items():
                    if value is not None:
                        old_fields[key] = value

                connection.execute(
                    """
                    UPDATE leads
                    SET customer_name_encrypted = ?,
                        reference_value = ?,
                        fields_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        encrypted_name,
                        reference_value,
                        json.dumps(old_fields),
                        existing_lead["id"]
                    )
                )

                duplicates_merged += 1

            else:

                connection.execute(
                    """
                    INSERT INTO leads (
                        workflow_id,
                        phone_hash,
                        phone_encrypted,
                        customer_name_encrypted,
                        reference_value,
                        batch_id,
                        fields_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow_id,
                        phone_hash,
                        encrypted_phone,
                        encrypted_name,
                        reference_value,
                        batch_id,
                        json.dumps(fields)
                    )
                )

        # Save rejected rows without customer PII
        for rejected in result["rejected"]:

            connection.execute(
                """
                INSERT INTO rejections (
                    workflow_id,
                    batch_id,
                    row_number,
                    reason
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    batch_id,
                    rejected["row_number"],
                    rejected["reason"]
                )
            )

        # Record successful file ingestion
        connection.execute(
            """
            INSERT INTO ingested_files (
                file_path,
                file_hash
            )
            VALUES (?, ?)
            """,
            (file_path, file_hash)
        )

        connection.commit()

        return {
            "status": "success",
            "total_rows": result["total_rows"],
            "accepted": len(result["accepted"]),
            "rejected": len(result["rejected"]),
            "duplicates_merged": duplicates_merged,
            "field_warnings": result["field_warnings"]
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

