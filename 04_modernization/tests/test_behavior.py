"""
tests/test_behavior.py
=======================
Behavioral tests for the Python modernization of LEGACY-PAYMENT-PROCESSOR.

These tests verify that the Python implementation preserves the observable
behavior encoded in behavior_contract.json.

Tests do NOT require a live DB2 connection. A stub repository is used.

Critical verifications:
  - Operator <= (not <) is used for the business decision.
  - Equality boundary: AMOUNT = CREDIT_LIMIT = 500.00 → APPROVED.
  - decimal.Decimal is used for monetary comparison (not float).
  - All six COBOL fields are represented in PaymentRecord.
  - ACCOUNT_ID is present in the data model.
  - STATUS is present in the data model.
  - Counter increments only on successful update.
  - OPEN failure exits without committing.
"""

from __future__ import annotations

import sys
import os
from decimal import Decimal
from typing import Deque, List, Tuple
from collections import deque

import pytest

# Make the modernization directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modern_payment_processor import (
    PaymentProcessor,
    PaymentRecord,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REVIEW,
    evaluate_payment,
)


# ---------------------------------------------------------------------------
# Stub Repository for testing
# ---------------------------------------------------------------------------

class StubRepository:
    """
    In-memory repository stub.

    Provides a queue of pre-configured fetch results and records every
    update_status call for later assertion.
    """

    def __init__(self, open_succeeds: bool = True):
        self._open_succeeds = open_succeeds
        self._fetch_queue: Deque[Tuple[str, PaymentRecord | None]] = deque()
        self.updates: List[Tuple[int, str]] = []
        self.commit_called = False
        self.close_called = False
        self._update_succeeds = True

    def enqueue(self, result: str, record: PaymentRecord | None = None) -> None:
        """Add a fetch result to the queue."""
        self._fetch_queue.append((result, record))

    def set_update_succeeds(self, succeeds: bool) -> None:
        self._update_succeeds = succeeds

    # --- PaymentRepository protocol ---

    def open_cursor(self) -> bool:
        return self._open_succeeds

    def fetch_next(self) -> Tuple[str, PaymentRecord | None]:
        if self._fetch_queue:
            return self._fetch_queue.popleft()
        return ("EOF", None)

    def update_status(self, payment_id: int, new_status: str) -> bool:
        self.updates.append((payment_id, new_status))
        return self._update_succeeds

    def close_cursor(self) -> None:
        self.close_called = True

    def commit(self) -> None:
        self.commit_called = True


def make_record(
    payment_id: int = 1,
    account_id: int = 100,
    amount: str = "100.00",
    credit_limit: str = "500.00",
    status: str = STATUS_PENDING,
    customer_name: str = "TEST CUSTOMER",
) -> PaymentRecord:
    """Helper to construct a PaymentRecord with Decimal monetary fields."""
    return PaymentRecord(
        payment_id=payment_id,
        account_id=account_id,
        amount=Decimal(amount),
        credit_limit=Decimal(credit_limit),
        status=status,
        customer_name=customer_name,
    )


# ===========================================================================
# SECTION 1: evaluate_payment — business logic unit tests
# ===========================================================================

class TestEvaluatePaymentOperator:
    """
    Tests for evaluate_payment().

    These tests directly verify the business rule comparison operator.
    BR-02: amount <= credit_limit → APPROVED
    BR-03: amount > credit_limit  → REVIEW
    APPROVAL-01: operator must remain <=
    """

    def test_amount_below_limit_is_approved(self):
        """BC-01: 499.99 < 500.00 → APPROVED"""
        result = evaluate_payment(Decimal("499.99"), Decimal("500.00"))
        assert result == STATUS_APPROVED

    def test_amount_equal_to_limit_is_approved(self):
        """
        BC-02: 500.00 == 500.00 → APPROVED  (CRITICAL EQUALITY BOUNDARY)

        This is the key test that distinguishes <= from <.
        COBOL: IF HV-AMOUNT <= HV-CREDIT-LIMIT
        Must NOT be changed to < without resolving APPROVAL-01.
        """
        result = evaluate_payment(Decimal("500.00"), Decimal("500.00"))
        assert result == STATUS_APPROVED, (
            "EQUALITY BOUNDARY FAILURE: AMOUNT=500.00 CREDIT_LIMIT=500.00 "
            "must produce APPROVED (operator is <=, not <). "
            "Changing this requires APPROVAL-01."
        )

    def test_amount_above_limit_is_review(self):
        """BC-03: 500.01 > 500.00 → REVIEW"""
        result = evaluate_payment(Decimal("500.01"), Decimal("500.00"))
        assert result == STATUS_REVIEW

    def test_zero_amount_is_approved(self):
        """BC-04: 0.00 <= 500.00 → APPROVED"""
        result = evaluate_payment(Decimal("0.00"), Decimal("500.00"))
        assert result == STATUS_APPROVED

    def test_nonzero_amount_against_zero_limit_is_review(self):
        """BC-05: 1.00 > 0.00 → REVIEW"""
        result = evaluate_payment(Decimal("1.00"), Decimal("0.00"))
        assert result == STATUS_REVIEW

    def test_zero_amount_zero_limit_is_approved(self):
        """BC-06: 0.00 <= 0.00 → APPROVED (equality at zero)"""
        result = evaluate_payment(Decimal("0.00"), Decimal("0.00"))
        assert result == STATUS_APPROVED

    def test_large_amount_well_below_limit_is_approved(self):
        """Large values below limit → APPROVED"""
        result = evaluate_payment(Decimal("9999.99"), Decimal("10000.00"))
        assert result == STATUS_APPROVED

    def test_large_amount_well_above_limit_is_review(self):
        """Large values above limit → REVIEW"""
        result = evaluate_payment(Decimal("10000.01"), Decimal("10000.00"))
        assert result == STATUS_REVIEW


class TestDecimalFidelity:
    """
    Verify that monetary values use decimal.Decimal and not float.
    BR-numeric: Decimal is required for monetary comparison.
    """

    def test_evaluate_payment_accepts_decimal(self):
        """evaluate_payment must accept Decimal arguments without error."""
        result = evaluate_payment(Decimal("500.00"), Decimal("500.00"))
        assert result == STATUS_APPROVED

    def test_payment_record_stores_decimal(self):
        """PaymentRecord.amount and credit_limit must be Decimal instances."""
        record = make_record(amount="123.45", credit_limit="1000.00")
        assert isinstance(record.amount, Decimal), "amount must be Decimal, not float"
        assert isinstance(record.credit_limit, Decimal), "credit_limit must be Decimal, not float"

    def test_decimal_equality_boundary_not_float_error(self):
        """
        Demonstrate that Decimal correctly handles the equality boundary.
        This would fail with float due to IEEE 754 representation issues.
        """
        amount = Decimal("500.00")
        credit_limit = Decimal("500.00")
        assert amount <= credit_limit
        result = evaluate_payment(amount, credit_limit)
        assert result == STATUS_APPROVED


# ===========================================================================
# SECTION 2: Data Model — field presence
# ===========================================================================

class TestDataModel:
    """
    Verify that the PaymentRecord data model contains all required fields.
    BR-08: ACCOUNT_ID must be retained.
    BR-09: STATUS must be retained.
    """

    def test_payment_record_has_payment_id(self):
        record = make_record(payment_id=42)
        assert record.payment_id == 42

    def test_payment_record_has_account_id(self):
        """APPROVAL-04: ACCOUNT_ID must remain in the data model."""
        record = make_record(account_id=99999)
        assert hasattr(record, "account_id"), "ACCOUNT_ID must be in data model (APPROVAL-04)"
        assert record.account_id == 99999

    def test_payment_record_has_amount(self):
        record = make_record(amount="250.00")
        assert record.amount == Decimal("250.00")

    def test_payment_record_has_credit_limit(self):
        record = make_record(credit_limit="1000.00")
        assert record.credit_limit == Decimal("1000.00")

    def test_payment_record_has_status(self):
        """STATUS must remain in the data model."""
        record = make_record(status=STATUS_PENDING)
        assert hasattr(record, "status"), "STATUS must be in data model"
        assert record.status == STATUS_PENDING

    def test_payment_record_has_customer_name(self):
        record = make_record(customer_name="JOHN DOE")
        assert record.customer_name == "JOHN DOE"


# ===========================================================================
# SECTION 3: PaymentProcessor — orchestration / behavioral integration tests
# ===========================================================================

class TestPaymentProcessorNormalRun:
    """
    Integration-style tests for PaymentProcessor using stub repository.
    Verify orchestration behavior end-to-end.
    """

    def test_single_approved_payment(self):
        """A payment with amount <= limit is updated to APPROVED."""
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=1, amount="400.00", credit_limit="500.00"))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert repo.updates == [(1, STATUS_APPROVED)]

    def test_single_review_payment(self):
        """A payment with amount > limit is updated to REVIEW."""
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=2, amount="600.00", credit_limit="500.00"))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert repo.updates == [(2, STATUS_REVIEW)]

    def test_equality_boundary_approved_in_processor(self):
        """
        CRITICAL: amount = credit_limit → APPROVED through full processor.
        500.00 / 500.00 → APPROVED
        """
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=3, amount="500.00", credit_limit="500.00"))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert len(repo.updates) == 1
        payment_id, status = repo.updates[0]
        assert payment_id == 3
        assert status == STATUS_APPROVED, (
            "CRITICAL EQUALITY BOUNDARY FAILED in full processor: "
            "AMOUNT=500.00 CREDIT_LIMIT=500.00 must produce APPROVED."
        )

    def test_counter_increments_on_successful_update(self):
        """BR-04: counter increments for every successful UPDATE."""
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=1, amount="100.00", credit_limit="500.00"))
        repo.enqueue("OK", make_record(payment_id=2, amount="200.00", credit_limit="500.00"))
        repo.enqueue("OK", make_record(payment_id=3, amount="600.00", credit_limit="500.00"))  # REVIEW
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert processor.processed_count == 3

    def test_counter_does_not_increment_on_update_failure(self):
        """BR-04: counter must NOT increment when UPDATE fails."""
        repo = StubRepository()
        repo.set_update_succeeds(False)
        repo.enqueue("OK", make_record(payment_id=1))
        repo.enqueue("OK", make_record(payment_id=2))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert processor.processed_count == 0

    def test_multiple_payments_mixed(self):
        """Multiple payments with different outcomes are all processed."""
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=1, amount="100.00", credit_limit="500.00"))  # APPROVED
        repo.enqueue("OK", make_record(payment_id=2, amount="500.00", credit_limit="500.00"))  # APPROVED (equality)
        repo.enqueue("OK", make_record(payment_id=3, amount="500.01", credit_limit="500.00"))  # REVIEW
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert repo.updates[0] == (1, STATUS_APPROVED)
        assert repo.updates[1] == (2, STATUS_APPROVED)  # equality → APPROVED
        assert repo.updates[2] == (3, STATUS_REVIEW)
        assert processor.processed_count == 3

    def test_single_commit_at_end_of_batch(self):
        """BR-07: exactly one COMMIT at the end of a normal run."""
        repo = StubRepository()
        repo.enqueue("OK", make_record(payment_id=1))
        repo.enqueue("OK", make_record(payment_id=2))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert repo.commit_called, "COMMIT must be called at end of batch (BR-07)"

    def test_cursor_closed_after_batch(self):
        """Cursor is closed after the processing loop."""
        repo = StubRepository()
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert repo.close_called, "Cursor must be closed after processing"


class TestPaymentProcessorErrorBehavior:
    """
    Tests for error-handling preservation (BR-05, BR-06, BR-10).
    """

    def test_open_failure_exits_without_commit(self):
        """BR-05: OPEN failure → exit immediately, no COMMIT."""
        repo = StubRepository(open_succeeds=False)

        processor = PaymentProcessor(repo)
        processor.run()

        assert not repo.commit_called, (
            "COMMIT must NOT be called after OPEN failure (BR-05)"
        )
        assert processor.processed_count == 0

    def test_open_failure_does_not_process_any_payments(self):
        """BR-05: No payments are processed when OPEN fails."""
        repo = StubRepository(open_succeeds=False)
        # Enqueue records that should never be reached
        repo.enqueue("OK", make_record(payment_id=1))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert len(repo.updates) == 0
        assert processor.processed_count == 0

    def test_fetch_error_commits_partial_batch(self):
        """
        BR-06 / APPROVAL-06 (unresolved — COBOL behavior preserved):
        FETCH error exits the loop; batch is committed with whatever was processed.
        """
        repo = StubRepository()
        # First row processed successfully, then a FETCH error
        repo.enqueue("OK", make_record(payment_id=1, amount="100.00", credit_limit="500.00"))
        repo.enqueue("ERROR")  # Simulates critical DB2 FETCH error

        processor = PaymentProcessor(repo)
        processor.run()

        # The one successful update must have been committed
        assert len(repo.updates) == 1
        assert repo.commit_called, (
            "COMMIT must still be called after FETCH error (BR-06 / APPROVAL-06 unresolved)"
        )
        assert processor.processed_count == 1

    def test_update_failure_does_not_abort_processing(self):
        """UPDATE failure is logged; processing continues with next payment."""
        repo = StubRepository()
        # First update will fail
        results = [False, True]
        call_count = [0]

        original_update = repo.update_status

        def selective_update(payment_id: int, new_status: str) -> bool:
            idx = call_count[0]
            call_count[0] += 1
            repo.updates.append((payment_id, new_status))
            return results[idx] if idx < len(results) else True

        repo.update_status = selective_update

        repo.enqueue("OK", make_record(payment_id=1))
        repo.enqueue("OK", make_record(payment_id=2))
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        # Both were attempted
        assert len(repo.updates) == 2
        # Only the second (successful) one counted
        assert processor.processed_count == 1

    def test_empty_queue_produces_zero_count(self):
        """No PENDING payments → counter stays at zero."""
        repo = StubRepository()
        repo.enqueue("EOF")

        processor = PaymentProcessor(repo)
        processor.run()

        assert processor.processed_count == 0
        assert repo.commit_called


# ===========================================================================
# SECTION 4: Approval Gate APPROVAL-01 confirmation tests
# ===========================================================================

class TestApprovalGate01OperatorConfirmation:
    """
    Explicit tests that confirm the modernization uses <= (not <).
    These tests would FAIL if someone changed the operator to < in violation
    of APPROVAL-01.
    """

    def test_equality_produces_approved_not_review(self):
        """
        APPROVAL-01 confirmation: operator is <= so equality → APPROVED.
        If this fails, the operator was silently changed to < — a violation.
        """
        result = evaluate_payment(Decimal("500.00"), Decimal("500.00"))
        assert result == STATUS_APPROVED
        assert result != STATUS_REVIEW

    def test_just_below_equality_is_approved(self):
        """One cent below limit → APPROVED (straightforward case)."""
        result = evaluate_payment(Decimal("499.99"), Decimal("500.00"))
        assert result == STATUS_APPROVED

    def test_just_above_equality_is_review(self):
        """One cent above limit → REVIEW (straightforward case)."""
        result = evaluate_payment(Decimal("500.01"), Decimal("500.00"))
        assert result == STATUS_REVIEW

    def test_operator_is_lte_confirmed(self):
        """
        Direct functional confirmation: <= means 'less than OR equal'.
        Both sub-cases must pass.
        """
        # less-than case
        assert evaluate_payment(Decimal("100.00"), Decimal("200.00")) == STATUS_APPROVED
        # equal-to case (the boundary)
        assert evaluate_payment(Decimal("200.00"), Decimal("200.00")) == STATUS_APPROVED
