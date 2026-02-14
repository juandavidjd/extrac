"""
V006 — Financial Reconciliation Engine
=======================================
Read-only audit + ethical cleanup of expired HOLDs.
Does NOT modify payment logic, Wompi webhooks, or confirmation functions.

Checks:
  A) Orphan Transactions  (CAPTURED payment without CONFIRMED booking)
  B) Zombie Cleanup       (HOLD past TTL → EXPIRED, related PENDING → EXPIRED)
  C) Shadow Accounting    (captured sum vs event count mismatch detection)
  D) Gateway Verification (stub — placeholder for future external reconciliation)
"""

import json
import logging
from datetime import date, datetime, timezone

from core.industries.turismo.db.client import pg_query, pg_execute, pg_available

logger = logging.getLogger("odi.reconciliation")


class FinancialReconciliator:
    """Daily financial reconciliation engine for ODI PAEM."""

    def __init__(self, db_session=None):
        # db_session accepted for interface compatibility.
        # Internally uses pg_query / pg_execute from db.client (pool-based).
        self._db_session = db_session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_daily_audit(self) -> dict:
        """Execute all reconciliation checks and persist the report."""
        if not pg_available():
            return {
                "error": "PostgreSQL unavailable — audit aborted",
                "audit_date": str(date.today()),
            }

        report = {
            "audit_date": str(date.today()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # A) Orphan transactions
        orphans = self._check_orphan_transactions()
        report["orphan_transactions"] = orphans["count"]
        report["orphan_tx_ids"] = orphans["tx_ids"]

        # B) Zombie cleanup
        cleanup = self._cleanup_expired_holds()
        report["expired_holds_closed"] = cleanup["holds_closed"]
        report["expired_pending_payments_closed"] = cleanup["payments_closed"]

        # C) Shadow accounting
        shadow = self._shadow_accounting()
        report["total_captured_today"] = float(shadow["total_captured_today"])
        report["payment_success_events_today"] = shadow["payment_success_events_today"]
        report["shadow_mismatch"] = shadow["shadow_mismatch"]

        # D) Gateway verification stub
        report["gateway_verification"] = "STUB_NOT_IMPLEMENTED"

        # Persist
        self._persist_report(report)

        logger.info("V006 reconciliation complete: %s", json.dumps(report, default=str))
        return report

    # ------------------------------------------------------------------
    # A) Orphan Transactions
    # ------------------------------------------------------------------

    def _check_orphan_transactions(self) -> dict:
        """Detect CAPTURED payments whose booking is NOT CONFIRMED."""
        sql = """
            SELECT p.transaction_id
            FROM odi_payments p
            LEFT JOIN odi_health_bookings b ON p.booking_id = b.booking_id
            WHERE p.status = 'CAPTURED'
              AND (b.status IS NULL OR b.status != 'CONFIRMED')
            LIMIT 50
        """
        rows = pg_query(sql) or []
        tx_ids = [r["transaction_id"] for r in rows]
        return {"count": len(tx_ids), "tx_ids": tx_ids}

    # ------------------------------------------------------------------
    # B) Zombie Cleanup — expired HOLDs + related PENDING payments
    # ------------------------------------------------------------------

    def _cleanup_expired_holds(self) -> dict:
        """Ethically close bookings past hold_expires_at and their pending payments."""
        holds_closed = 0
        payments_closed = 0

        # 1. Expire stale HOLDs
        expire_holds_sql = """
            UPDATE odi_health_bookings
            SET status = 'EXPIRED', updated_at = NOW()
            WHERE status = 'HOLD'
              AND hold_expires_at IS NOT NULL
              AND hold_expires_at < NOW()
            RETURNING booking_id, transaction_id
        """
        expired_rows = pg_query(expire_holds_sql) or []
        holds_closed = len(expired_rows)

        # Register an event per expired hold
        for row in expired_rows:
            pg_execute(
                """INSERT INTO odi_events
                   (event_type, transaction_id, booking_id, payload)
                   VALUES (%s, %s, %s, %s::jsonb)""",
                (
                    "PAEM.HOLD_EXPIRED",
                    row["transaction_id"],
                    row["booking_id"],
                    json.dumps({
                        "expired_at": datetime.now(timezone.utc).isoformat(),
                        "source": "V006_RECONCILIATION",
                    }),
                ),
            )

        # 2. Expire related PENDING payments
        if expired_rows:
            booking_ids = [r["booking_id"] for r in expired_rows]
            expire_payments_sql = """
                UPDATE odi_payments
                SET status = 'EXPIRED', updated_at = NOW()
                WHERE booking_id = ANY(%s)
                  AND status = 'PENDING'
                RETURNING transaction_id
            """
            pay_rows = pg_query(expire_payments_sql, (booking_ids,)) or []
            payments_closed = len(pay_rows)

        return {"holds_closed": holds_closed, "payments_closed": payments_closed}

    # ------------------------------------------------------------------
    # C) Shadow Accounting
    # ------------------------------------------------------------------

    def _shadow_accounting(self) -> dict:
        """Compare captured payments total vs payment-success event count for today."""
        captured_sql = """
            SELECT COALESCE(SUM(amount), 0) AS total_captured,
                   COUNT(*) AS captured_count
            FROM odi_payments
            WHERE status = 'CAPTURED'
              AND captured_at::date = CURRENT_DATE
        """
        cap_row = (pg_query(captured_sql) or [{}])[0]
        total_captured = cap_row.get("total_captured", 0)
        captured_count = cap_row.get("captured_count", 0)

        events_sql = """
            SELECT COUNT(*) AS event_count
            FROM odi_events
            WHERE event_type = 'PAEM.PAYMENT_SUCCESS'
              AND created_at::date = CURRENT_DATE
        """
        evt_row = (pg_query(events_sql) or [{}])[0]
        event_count = evt_row.get("event_count", 0)

        mismatch = (captured_count != event_count) or (
            total_captured > 0 and event_count == 0
        )

        return {
            "total_captured_today": total_captured,
            "payment_success_events_today": event_count,
            "shadow_mismatch": mismatch,
        }

    # ------------------------------------------------------------------
    # D) Gateway Verification — STUB
    # ------------------------------------------------------------------

    def verify_with_gateway(self, transaction_id: str) -> dict:
        """
        STUB: Future integration with payment gateway reconciliation API.

        When activated, this method will:
        - Query Wompi GET /v1/transactions/{gateway_reference}
        - Compare gateway status vs local odi_payments.status
        - Flag discrepancies for manual review

        NOT IMPLEMENTED — placeholder for external audit phase.
        """
        return {
            "status": "NOT_IMPLEMENTED",
            "transaction_id": transaction_id,
            "message": (
                "Gateway verification pending implementation. "
                "Will query Wompi GET /v1/transactions/{id} when activated."
            ),
        }

    # ------------------------------------------------------------------
    # Persistence — report + event sourcing
    # ------------------------------------------------------------------

    def _persist_report(self, report: dict) -> None:
        """Save report to odi_reconciliation_reports and emit odi_events."""
        summary_json = json.dumps(report, default=str)

        # 1. Insert into reports table
        pg_execute(
            """INSERT INTO odi_reconciliation_reports (period, summary)
               VALUES (CURRENT_DATE, %s::jsonb)""",
            (summary_json,),
        )

        # 2. Emit event
        pg_execute(
            """INSERT INTO odi_events
               (event_type, payload)
               VALUES (%s, %s::jsonb)""",
            ("SYSTEM.RECONCILIATION_REPORT", summary_json),
        )


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    """Run reconciliation and print JSON report to stdout."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    reconciliator = FinancialReconciliator()
    report = reconciliator.run_daily_audit()

    json.dump(report, sys.stdout, indent=2, default=str)
    print()  # trailing newline

    if report.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
