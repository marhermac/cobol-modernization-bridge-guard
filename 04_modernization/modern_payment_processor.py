"""
modern_payment_processor.py
============================
Python modernization of LEGACY-PAYMENT-PROCESSOR (COBOL).

Preserved behaviors (from behavior_contract.json):
  - BR-01: Only PENDING payments are processed.
  - BR-02: AMOUNT <= CREDIT_LIMIT → APPROVED  (operator is <=, NOT <)
  - BR-03: AMOUNT > CREDIT_LIMIT → REVIEW
  - BR-04: Counter increments only on successful UPDATE.
  - BR-05: OPEN failure exits without commit.
  - BR-06: FETCH error terminates loop; batch is committed (no rollback).
  - BR-07: Single COMMIT at end of batch (no per-row commits).
  - BR-08: ACCOUNT_ID is part of the data model (APPROVAL-04 unresolved).
  - BR-09: STATUS is fetched but not re-evaluated.
  - BR-10: CLOSE/COMMIT errors are silently ignored (APPROVAL-02 unresolved).

Unresolved approval gates: APPROVAL-01 through APPROVAL-06.
All unresolved gates default to COBOL legacy behavior.

IMPORTANT — Numeric fidelity:
  All monetary values (amount, credit_limit) use decimal.Decimal.
  float is NOT used for monetary comparison.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Protocol, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status constants — mirrors COBOL WS-PENDING / WS-APPROVED / WS-REVIEW
# ---------------------------------------------------------------------------

STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REVIEW = "REVIEW"


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class PaymentRecord:
    """
    Represents one row fetched from LEGACY.PAYMENT_QUEUE.

    All six fields fetched by the COBOL FETCH statement are retained:
      - payment_id    → HV-PAYMENT-ID    (PIC S9(9) COMP)
      - account_id    → HV-ACCOUNT-ID    (PIC S9(9) COMP)   [APPROVAL-04]
      - amount        → HV-AMOUNT        (PIC S9(7)V99 COMP-3 → Decimal)
      - credit_limit  → HV-CREDIT-LIMIT  (PIC S9(7)V99 COMP-3 → Decimal)
      - status        → HV-STATUS        (PIC X(10))
      - customer_name → HV-CUSTOMER-NAME (PIC X(40))

    Fields account_id and status are preserved per APPROVAL-04 (unresolved).
    Monetary fields use Decimal for exact representation (no float).
    """
    payment_id: int
    account_id: int       # APPROVAL-04: retained per default (COBOL behavior)
    amount: Decimal       # MUST be Decimal — not float
    credit_limit: Decimal  # MUST be Decimal — not float
    status: str           # Fetched value (always 'PENDING' due to cursor filter)
    customer_name: str


# ---------------------------------------------------------------------------
# Business Logic
# ---------------------------------------------------------------------------

def evaluate_payment(amount: Decimal, credit_limit: Decimal) -> str:
    """
    Determine the outcome status for a payment.

    Implements BR-02 and BR-03.

    The comparison operator is <= (less-than-or-equal).
    This is the COBOL behavior: IF HV-AMOUNT <= HV-CREDIT-LIMIT.

    CRITICAL: The equality case (amount == credit_limit) MUST return APPROVED.
    Changing this operator requires resolution of APPROVAL-01.

    Examples:
        >>> evaluate_payment(Decimal("499.99"), Decimal("500.00"))
        'APPROVED'
        >>> evaluate_payment(Decimal("500.00"), Decimal("500.00"))
        'APPROVED'
        >>> evaluate_payment(Decimal("500.01"), Decimal("500.00"))
        'REVIEW'
    """
    # BR-02 / BR-03: COBOL IF HV-AMOUNT <= HV-CREDIT-LIMIT
    # APPROVAL-01 (UNRESOLVED): operator preserved as <= per COBOL legacy behavior.
    if amount <= credit_limit:
        return STATUS_APPROVED
    else:
        return STATUS_REVIEW


# ---------------------------------------------------------------------------
# Repository Protocol (database abstraction)
# ---------------------------------------------------------------------------

class PaymentRepository(Protocol):
    """
    Abstract interface for database access.

    Separates business logic from DB2 implementation.
    Tests inject a stub; production uses a real DB2 implementation.
    """

    def open_cursor(self) -> bool:
        """
        Open the payment cursor.
        Returns True on success, False on failure (mirrors OPEN SQLCODE check).
        """
        ...

    def fetch_next(self) -> Tuple[str, PaymentRecord | None]:
        """
        Fetch the next PENDING payment row.

        Returns:
            ('OK', PaymentRecord)    — successful fetch
            ('EOF', None)            — SQLCODE 100 (no more rows)
            ('ERROR', None)          — non-zero, non-100 SQLCODE
        """
        ...

    def update_status(self, payment_id: int, new_status: str) -> bool:
        """
        Update the STATUS of the current row (WHERE CURRENT OF cursor equivalent).
        Returns True on success, False on failure.
        """
        ...

    def close_cursor(self) -> None:
        """
        Close the cursor.
        BR-10: errors silently ignored (APPROVAL-02 unresolved).
        """
        ...

    def commit(self) -> None:
        """
        Commit the current transaction.
        BR-07: single commit at end of batch.
        BR-10: errors silently ignored (APPROVAL-02 unresolved).
        """
        ...


# ---------------------------------------------------------------------------
# Processing Orchestration
# ---------------------------------------------------------------------------

class PaymentProcessor:
    """
    Orchestrates the payment processing run.

    Preserves the COBOL program flow exactly:
      0000-MAIN → 1000-PROCESS-PAYMENTS → 2000-PROCESS-PAYMENT

    Transaction behavior:
      - Single COMMIT at the end of the batch (BR-07, APPROVAL-05 unresolved).
      - No ROLLBACK anywhere in the implementation (mirrors COBOL).
      - FETCH error commits whatever was processed (BR-06, APPROVAL-06 unresolved).
    """

    def __init__(self, repository: PaymentRepository) -> None:
        self._repo = repository
        self._processed_count = 0

    @property
    def processed_count(self) -> int:
        """Number of successfully updated payments (BR-04)."""
        return self._processed_count

    def run(self) -> None:
        """
        Main processing entry point. Mirrors COBOL 0000-MAIN.

        BR-05: OPEN failure exits without COMMIT.
        BR-07: Single COMMIT at end of batch.
        """
        logger.info("--------------------------------------------")
        logger.info(" LEGACY PAYMENT PROCESSOR")
        logger.info("--------------------------------------------")

        # --- OPEN PAYMENT-CURSOR (BR-05) ---
        opened = self._repo.open_cursor()
        if not opened:
            # COBOL: DISPLAY "ERROR OPENING PAYMENT CURSOR" / GOBACK
            # No COMMIT — mirrors COBOL GOBACK without commit on OPEN failure.
            logger.error("ERROR OPENING PAYMENT CURSOR")
            return  # exits without commit (BR-05)

        # --- PERFORM 1000-PROCESS-PAYMENTS UNTIL END-OF-DATA ---
        self._process_all_payments()

        # --- CLOSE PAYMENT-CURSOR (BR-10: error silently ignored) ---
        self._repo.close_cursor()

        # --- COMMIT (BR-07: single batch commit; BR-10: error silently ignored) ---
        self._repo.commit()

        # --- Final summary ---
        logger.info("PAYMENTS PROCESSED: %d", self._processed_count)
        logger.info("PROCESS COMPLETE.")

    def _process_all_payments(self) -> None:
        """
        Fetch-and-process loop. Mirrors COBOL PERFORM UNTIL END-OF-DATA.

        BR-06: A FETCH error sets end-of-data; loop exits; batch proceeds to commit.
        """
        while True:
            result, record = self._repo.fetch_next()

            if result == "EOF":
                # SQLCODE 100 — normal end of data (WHEN 100 SET END-OF-DATA)
                break

            if result == "ERROR":
                # WHEN OTHER — DISPLAY critical error, SET END-OF-DATA
                # BR-06: no ROLLBACK; the loop exits and commit still proceeds.
                logger.critical("CRITICAL DB2 ERROR: FETCH failed")
                break  # APPROVAL-06 unresolved: partial commit proceeds

            # result == 'OK', record is a PaymentRecord
            self._process_one_payment(record)

    def _process_one_payment(self, record: PaymentRecord) -> None:
        """
        Process a single payment record. Mirrors COBOL 2000-PROCESS-PAYMENT.

        BR-02 / BR-03: evaluate amount vs credit_limit.
        BR-04: counter increments only on successful update.
        """
        logger.info("PAYMENT ID: %d", record.payment_id)
        logger.info("CUSTOMER: %s", record.customer_name)
        logger.info("AMOUNT: %s", record.amount)
        logger.info("CREDIT LIMIT: %s", record.credit_limit)

        # Business decision (BR-02 / BR-03)
        new_status = evaluate_payment(record.amount, record.credit_limit)

        # Database update
        success = self._repo.update_status(record.payment_id, new_status)

        if not success:
            # COBOL: DISPLAY "ERROR UPDATING PAYMENT: " + SQLCODE
            # Processing continues to next payment (no abort, no rollback)
            logger.error("ERROR UPDATING PAYMENT: %d", record.payment_id)
        else:
            # BR-04: counter increments only on successful UPDATE
            self._processed_count += 1
            logger.info("PAYMENT STATUS UPDATED.")
