
from solution.database import get_connection


def create_link_table(connection):
    """
    Create a table to store event-to-lead relationships.
    """

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS event_lead_links (
            event_id TEXT PRIMARY KEY,
            lead_id INTEGER NOT NULL,
            link_method TEXT NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id),
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
        """
    )


def link_events_to_leads():
    """
    Link events with customer leads.
    """

    results = {
        "directly_linked": 0,
        "override_linked": 0,
        "orphaned": 0
    }

    connection = get_connection()

    try:
        create_link_table(connection)

        # Clear old links and quarantine records.
        connection.execute("DELETE FROM event_lead_links")
        connection.execute("DELETE FROM event_quarantine")

        # 1. Match events using workflow ID and phone hash.
        direct_events = connection.execute(
            """
            SELECT e.event_id, l.id AS lead_id
            FROM events e
            JOIN leads l
              ON e.workflow_id = l.workflow_id
             AND e.phone_hash = l.phone_hash
            WHERE e.phone_hash IS NOT NULL
            """
        ).fetchall()

        for event in direct_events:

            connection.execute(
                """
                INSERT INTO event_lead_links
                    (event_id, lead_id, link_method)
                VALUES (?, ?, ?)
                """,
                (event["event_id"], event["lead_id"], "phone_hash")
            )

            results["directly_linked"] += 1

        # 2. Match override events using call ID.
        override_events = connection.execute(
            """
            SELECT e.event_id, related.id AS lead_id
            FROM events e
            JOIN events related_event
              ON related_event.call_id = e.call_id
             AND related_event.workflow_id = e.workflow_id
             AND related_event.phone_hash IS NOT NULL
            JOIN leads related
              ON related.workflow_id = related_event.workflow_id
             AND related.phone_hash = related_event.phone_hash
            WHERE e.event_type = 'disposition.override'
              AND e.call_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM event_lead_links existing
                  WHERE existing.event_id = e.event_id
              )
            GROUP BY e.event_id
            """
        ).fetchall()

        for event in override_events:

            connection.execute(
                """
                INSERT INTO event_lead_links
                    (event_id, lead_id, link_method)
                VALUES (?, ?, ?)
                """,
                (event["event_id"], event["lead_id"], "call_id")
            )

            results["override_linked"] += 1

        # 3. Find events that are not linked.
        orphan_events = connection.execute(
            """
            SELECT e.event_id, e.event_type, e.phone_hash
            FROM events e
            LEFT JOIN event_lead_links linked
              ON linked.event_id = e.event_id
            WHERE linked.event_id IS NULL
            """
        ).fetchall()

        # 4. Save unmatched events in quarantine.
        for event in orphan_events:

            if event["event_type"] == "disposition.override":
                reason = "orphan_call_not_found"
            elif event["phone_hash"] is None:
                reason = "missing_or_invalid_phone"
            else:
                reason = "orphan_lead_not_found"

            connection.execute(
                """
                INSERT INTO event_quarantine (event_id, reason)
                VALUES (?, ?)
                """,
                (event["event_id"], reason)
            )

            results["orphaned"] += 1

        connection.commit()

        return results

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
