
import json

from solution.lead_processor import create_header_mapping

with open("schemas/motor_renewal.json", "r", encoding="utf-8") as file:
    schema = json.load(file)

csv_headers = [
    "Customer Name",
    "Mobile No",
    "Policy No",
    "Expiry Date",
    "Premium",
    "Language"
]

mapping = create_header_mapping(csv_headers, schema)

print("CSV Header Mapping:")

for field, csv_column in mapping.items():
    print(field, "->", csv_column)

