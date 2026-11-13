\# Assignment A: Interaction Ledger \& Reporting Pipeline



\## Project Overview



This project implements a data ingestion, validation, event-linking, analytics, and reporting pipeline for customer interaction data.



The pipeline processes lead CSV files and call-event JSONL files for two workflows:



\- Motor Renewal

\- Policy Feedback



SQLite is used to store lead and event records.



\## Technologies Used



\- Python

\- SQLite

\- SQL

\- CSV and JSONL processing

\- Pandas-compatible data processing concepts

\- Python cryptography (Fernet)

\- HMAC-SHA256

\- JSON reporting



\## Implemented Features



\### 1. Lead Data Processing



\- Reads CSV files from multiple data drops.

\- Normalizes CSV headers and supports aliases.

\- Validates required and optional fields.

\- Normalizes Indian phone numbers.

\- Validates dates, decimal values, and enum fields.

\- Records rejected rows and optional-field warnings.

\- Merges duplicate leads using workflow ID and phone hash.



\### 2. Data Security



\- Encrypts customer phone numbers and names using Fernet.

\- Uses HMAC-SHA256 for phone lookup.

\- Masks phone numbers in reports.

\- Avoids storing customer PII in rejection reports.



\### 3. Event Processing



\- Reads JSONL event files.

\- Validates event structure.

\- Detects duplicate event IDs.

\- Validates disposition codes.

\- Normalizes event timestamps to IST.

\- Links events to leads.

\- Quarantines orphan events.

\- Supports linking disposition overrides using call IDs.



\### 4. Analytics



\- Calculates total and connected calls.

\- Determines effective dispositions.

\- Identifies successful calls.

\- Calculates lead buckets:

&#x20; - yet\_to\_reach\_out

&#x20; - in\_progress\_telephony\_failed

&#x20; - in\_progress\_dialed

&#x20; - completed



\### 5. Reports Generated



The reports are generated in the `reports/` directory.



1\. `batch\_summary.csv`

2\. `daily\_overview.csv`

3\. `lead\_report.csv`

4\. `rejections.csv`

5\. `data\_quality.json`



\## Running the Project



Generate sample input data:



```powershell

python tools/generate\_data.py --seed 42 --scale small --out data

```



After processing the lead and event input files and creating the database links, generate the reports:



```powershell

python -m solution.report\_generator

```



\## Current Dataset Results



| Metric | Result |

|---|---:|

| Lead rows processed | 2057 |

| Rejected lead rows | 108 |

| Duplicate lead rows merged | 57 |

| Unique leads | 1892 |

| Event lines processed | 8745 |

| Malformed events | 8 |

| Duplicate event IDs | 237 |

| Unknown disposition events | 19 |

| Orphan events | 461 |

| Linked events | 8020 |



\## Project Structure



```text

assignment-a-data/

├── schemas/

├── tools/

├── data/

├── solution/

│   ├── database.py

│   ├── validators.py

│   ├── security.py

│   ├── lead\_processor.py

│   ├── event\_processor.py

│   ├── event\_ingestion.py

│   ├── event\_linker.py

│   ├── analytics.py

│   └── report\_generator.py

├── reports/

│   ├── batch\_summary.csv

│   ├── daily\_overview.csv

│   ├── lead\_report.csv

│   ├── rejections.csv

│   └── data\_quality.json

├── assignment.db

├── SUBMISSION.md

└── AI\_USAGE.md

```



\## Conclusion



The project implements the core data processing and reporting workflow, including validation, secure storage, event linking, analytics, and generation of the five required reports.

