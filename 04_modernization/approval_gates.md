# Phase 6 — Human Approval Gates

**Scope:** Every unresolved semantic decision between COBOL behavior, Requirements V1, and Requirements V2.

**Default rule:** If an approval gate is NOT explicitly resolved, the modernization preserves LEGACY COBOL BEHAVIOR.

---

## APPROVAL-01 — Comparison Operator: `<=` vs `<`

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-01                                                              |
| Category               | Business Rule — Operator Semantics                                       |
| Source A (COBOL)       | `IF HV-AMOUNT <= HV-CREDIT-LIMIT` — operator is **<=** (less-than-or-equal) |
| Source B (V1)          | "less than **or equal to**" — matches COBOL (`<=`)                       |
| Source C (V2)          | "less than" — operator is **<** (strict less-than)                       |
| Concrete Example       | AMOUNT = 500.00, CREDIT_LIMIT = 500.00 → COBOL/V1: **APPROVED** — V2: **REVIEW** |
| Business Consequence   | Under V2, a payment that exactly meets the credit limit would be escalated to manual review instead of being automatically approved. This affects any customer whose payment amount exactly equals their credit limit. |
| Default (if unresolved) | **Preserve COBOL behavior: use `<=`; equality case → APPROVED**         |
| Recommendation         | Escalate to business owner. The change from `<=` to `<` is a material business rule change affecting the equality boundary. Confirm which behavior is correct for production. |
| **Status**             | **UNRESOLVED — awaiting human decision**                                 |

---

## APPROVAL-02 — CLOSE / COMMIT Error Handling

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-02                                                              |
| Category               | Error Handling — Silent Failure                                          |
| Source A (COBOL)       | CLOSE and COMMIT have no SQLCODE check. Errors are silently ignored. (lines 100–106) |
| Source B+C (V1/V2)     | "A database error must not be silently ignored."                         |
| Concrete Example       | COMMIT fails after 100 updates → COBOL displays "PROCESS COMPLETE" and reports 100 processed; data was never committed. |
| Business Consequence   | High-severity data integrity risk: the processor reports success when in fact no records were persisted. |
| Default (if unresolved) | **Preserve COBOL behavior: do not check SQLCODE after CLOSE or COMMIT** |
| Recommendation         | Add SQLCODE checks after CLOSE and COMMIT. This aligns with V1/V2 REQ-05 and is clearly a defect in the legacy code. However, changing this behavior requires explicit authorization because it would alter observable program behavior (error path vs silent continue). |
| **Status**             | **UNRESOLVED — awaiting human decision**                                 |

---

## APPROVAL-03 — Exit Code Behavior

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-03                                                              |
| Category               | Error Handling — Exit Semantics                                          |
| Source A (COBOL)       | All exits use `GOBACK`. There is no differentiation between normal exit and error exit at the OS return code level. |
| Source B+C (V1/V2)     | No requirement specified for exit codes.                                 |
| Concrete Example       | OPEN failure → GOBACK (same instruction as normal completion). OS receives the same return code in both cases. |
| Business Consequence   | Job schedulers or orchestrators that rely on return codes cannot distinguish success from failure. |
| Default (if unresolved) | **Preserve COBOL behavior: no differentiated exit code**                |
| Recommendation         | Consider returning non-zero exit code on error paths. This is a modernization improvement but constitutes a behavioral change. |
| **Status**             | **UNRESOLVED — awaiting human decision**                                 |

---

## APPROVAL-04 — ACCOUNT_ID Presence in SELECT and Data Model

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-04                                                              |
| Category               | Data Interface — Field Presence                                          |
| Source A (COBOL)       | ACCOUNT_ID is fetched into HV-ACCOUNT-ID (lines 60, 127) but is never used in any business decision or DISPLAY output. |
| Source B+C (V1/V2)     | REQ-04 requires ACCOUNT_ID to be preserved.                             |
| Concrete Example       | A query that returns ACCOUNT_ID = 98765 results in HV-ACCOUNT-ID = 98765. No downstream process reads this value. |
| Business Consequence   | Dropping ACCOUNT_ID from the Python data model would narrow the data interface. If any future or downstream system relies on it being present, removal could break integration. |
| Default (if unresolved) | **Preserve COBOL behavior: include ACCOUNT_ID in data model and SELECT**|
| Recommendation         | Keep ACCOUNT_ID in the data model. Cost is zero and removal carries risk. |
| **Status**             | **UNRESOLVED — preserving legacy behavior (ACCOUNT_ID retained)**        |

---

## APPROVAL-05 — Transaction Granularity

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-05                                                              |
| Category               | Transaction Semantics                                                    |
| Source A (COBOL)       | Single COMMIT at the end of the batch run. No per-row commits. All updates are atomic as one unit of work. |
| Source B+C (V1/V2)     | No explicit requirement on transaction granularity.                      |
| Concrete Example       | 200 payments processed → all 200 updates committed in a single COMMIT; if the COMMIT fails, all 200 are lost. |
| Business Consequence   | Converting to per-row commits would: (a) make individual failures non-atomic (partial state possible), (b) improve resilience but change the rollback semantics, (c) change observable behavior for failure scenarios. |
| Default (if unresolved) | **Preserve COBOL behavior: single COMMIT after full batch**             |
| Recommendation         | Confirm with business owner. For high-volume batches, single-commit is a scalability and durability risk. However, changing to per-row commits is a semantic change that must be explicitly authorized. |
| **Status**             | **UNRESOLVED — awaiting human decision**                                 |

---

## APPROVAL-06 — Partial Commit After FETCH Error

| Field                  | Value                                                                    |
|------------------------|--------------------------------------------------------------------------|
| Approval ID            | APPROVAL-06                                                              |
| Category               | Transaction Semantics — Error Recovery                                   |
| Source A (COBOL)       | When FETCH fails (non-0, non-100 SQLCODE), the loop exits via SET END-OF-DATA. The program then proceeds unconditionally to CLOSE and COMMIT. Rows updated before the FETCH error ARE committed. |
| Source B+C (V1/V2)     | "A database error must not be silently ignored." No specific behavior defined for mid-batch failure. |
| Concrete Example       | 50 of 100 rows fetched and updated → FETCH error on row 51 → loop exits → COMMIT → the first 50 updates are permanently persisted. Rows 51–100 remain PENDING. |
| Business Consequence   | Partial batch commit leaves data in a split state. The remaining PENDING rows may be reprocessed in the next run (if the program is re-executed), which may or may not be the intended recovery behavior. |
| Default (if unresolved) | **Preserve COBOL behavior: commit partial batch after FETCH error**     |
| Recommendation         | Determine whether a FETCH error should roll back all updates or commit the partial set. This is a critical business decision for data integrity. A ROLLBACK would prevent partial state but change observable legacy behavior. |
| **Status**             | **UNRESOLVED — awaiting human decision**                                 |

---

## Approval Gates Summary

| Gate ID     | Topic                              | Default Behavior        | Status               |
|-------------|------------------------------------|-------------------------|----------------------|
| APPROVAL-01 | Operator `<=` vs `<`              | Preserve `<=` (COBOL)   | **UNRESOLVED**       |
| APPROVAL-02 | CLOSE/COMMIT silent error          | Preserve silent ignore  | **UNRESOLVED**       |
| APPROVAL-03 | Exit code behavior                 | Preserve GOBACK only    | **UNRESOLVED**       |
| APPROVAL-04 | ACCOUNT_ID in SELECT/model         | Preserve ACCOUNT_ID     | **UNRESOLVED** (retained per default) |
| APPROVAL-05 | Transaction granularity            | Preserve single COMMIT  | **UNRESOLVED**       |
| APPROVAL-06 | Partial commit on FETCH error      | Preserve partial commit | **UNRESOLVED**       |

**All gates are UNRESOLVED. The Python modernization preserves COBOL legacy behavior for every gate.**
