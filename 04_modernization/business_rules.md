# Phase 2 — Business Rule Extraction

**Source:** `01_legacy/legacy_payment_processor.cbl` (behavioral baseline)

All rules are extracted from observable COBOL behavior. No inference beyond
the source code is made.

---

## BR-01 — Filter: Only PENDING Payments Are Processed

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-01                                              |
| Description   | Only rows with STATUS = 'PENDING' are selected for processing. |
| COBOL Evidence | `WHERE STATUS = :WS-PENDING` in cursor declaration (line 66). WS-PENDING has value 'PENDING'. |
| Operator      | = (equality)                                       |
| Input Fields  | STATUS (from LEGACY.PAYMENT_QUEUE)                 |
| Output/Result | Rows not matching STATUS = 'PENDING' are never fetched, never evaluated, never updated. |
| Edge Cases    | Status values of 'APPROVED', 'REVIEW', or any other value are excluded. |
| Confidence    | HIGH — direct SQL WHERE clause, unambiguous.       |

---

## BR-02 — Approve When Amount ≤ Credit Limit

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-02                                              |
| Description   | If the payment amount is less than or equal to the credit limit, the payment is approved. |
| COBOL Evidence | `IF HV-AMOUNT <= HV-CREDIT-LIMIT` (line 182); `UPDATE ... SET STATUS = :WS-APPROVED` (lines 185–188). |
| **Operator**  | **`<=` (less-than-or-equal) — CRITICAL**          |
| Input Fields  | HV-AMOUNT (PIC S9(7)V99 COMP-3), HV-CREDIT-LIMIT (PIC S9(7)V99 COMP-3) |
| Output/Result | STATUS updated to 'APPROVED' in LEGACY.PAYMENT_QUEUE. |
| Edge Cases    | **When AMOUNT = CREDIT_LIMIT exactly, the result is APPROVED** (not REVIEW). This is the boundary case defined by the `<=` operator. |
| Confidence    | HIGH — direct conditional, explicit operator, unambiguous.  |

---

## BR-03 — Review When Amount > Credit Limit

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-03                                              |
| Description   | If the payment amount is greater than the credit limit, the payment is placed in review. |
| COBOL Evidence | `ELSE` branch of the IF at line 182; `UPDATE ... SET STATUS = :WS-REVIEW` (lines 192–196). |
| Operator      | `>` (implicit ELSE of <=)                          |
| Input Fields  | HV-AMOUNT, HV-CREDIT-LIMIT                         |
| Output/Result | STATUS updated to 'REVIEW' in LEGACY.PAYMENT_QUEUE.|
| Edge Cases    | Only activates when AMOUNT > CREDIT_LIMIT. The equality case belongs to BR-02. |
| Confidence    | HIGH — direct ELSE branch.                         |

---

## BR-04 — Counter Increments Only on Successful UPDATE

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-04                                              |
| Description   | The processed counter is incremented only when the UPDATE SQL statement succeeds. |
| COBOL Evidence | `IF SQLCODE NOT = 0 ... ELSE ADD 1 TO WS-PROCESSED-COUNT` (lines 204–216). |
| Operator      | SQLCODE = 0 (success condition)                    |
| Input Fields  | SQLCODE (after UPDATE)                             |
| Output/Result | WS-PROCESSED-COUNT += 1 on success. On UPDATE failure, counter is NOT incremented and processing continues. |
| Edge Cases    | A payment that is fetched but fails to update is not counted. |
| Confidence    | HIGH — explicit conditional around ADD statement.  |

---

## BR-05 — OPEN Failure Exits Without Commit

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-05                                              |
| Description   | If the cursor OPEN fails, the program exits immediately via GOBACK without performing any COMMIT. |
| COBOL Evidence | `IF SQLCODE NOT = 0 ... DISPLAY ... GOBACK END-IF` (lines 91–95) immediately after OPEN. |
| Operator      | SQLCODE ≠ 0                                        |
| Input Fields  | SQLCODE (after OPEN)                               |
| Output/Result | GOBACK — no COMMIT, no processing.                 |
| Edge Cases    | No partial commits can occur when OPEN fails.      |
| Confidence    | HIGH — explicit conditional with GOBACK.           |

---

## BR-06 — FETCH Error Terminates Loop; Batch Is Committed

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-06                                              |
| Description   | A non-zero, non-100 SQLCODE on FETCH sets END-OF-DATA, terminating the loop. Processing then proceeds to CLOSE and COMMIT. Any rows already updated ARE committed. |
| COBOL Evidence | `WHEN OTHER ... SET END-OF-DATA TO TRUE` (lines 142–147); COMMIT follows the PERFORM loop unconditionally. |
| Operator      | SQLCODE ≠ 0 AND SQLCODE ≠ 100                      |
| Input Fields  | SQLCODE (after FETCH)                              |
| Output/Result | Loop exits; CLOSE and COMMIT execute; partial batch is committed. |
| Edge Cases    | This may commit a partial batch silently; no error is raised to the COMMIT or CLOSE level. |
| Confidence    | HIGH — direct EVALUATE, unconditional COMMIT path confirmed. |

---

## BR-07 — Single COMMIT at End of Batch

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-07                                              |
| Description   | All payment updates within a processing run are committed in a single COMMIT statement executed after the loop ends and the cursor is closed. |
| COBOL Evidence | `EXEC SQL COMMIT END-EXEC` (lines 104–106), after CLOSE and after the PERFORM loop. |
| Operator      | N/A                                                |
| Input Fields  | N/A                                                |
| Output/Result | All updates committed atomically as one unit of work. |
| Edge Cases    | If COMMIT fails, the failure is silently ignored (no SQLCODE check). |
| Confidence    | HIGH — single COMMIT, no per-row commit exists in the program. |

---

## BR-08 — ACCOUNT_ID Is Part of the Data Interface

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-08                                              |
| Description   | ACCOUNT_ID is fetched from the database into HV-ACCOUNT-ID. It is part of the fetched record, even though it is not used in the business decision logic. |
| COBOL Evidence | `ACCOUNT_ID` in SELECT (line 60); `HV-ACCOUNT-ID` in FETCH INTO (line 127). |
| Operator      | N/A                                                |
| Input Fields  | ACCOUNT_ID from LEGACY.PAYMENT_QUEUE               |
| Output/Result | Stored in HV-ACCOUNT-ID; not used or displayed.   |
| Edge Cases    | Removing it from the data model would narrow the interface contract. |
| Confidence    | HIGH — present in SELECT and FETCH; medium confidence on intent since it is unused downstream. |

---

## BR-09 — STATUS Is Fetched But Not Independently Re-Evaluated

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-09                                              |
| Description   | HV-STATUS is fetched into WORKING-STORAGE. Because the cursor WHERE clause already filters for STATUS = 'PENDING', HV-STATUS will always be 'PENDING' when fetched. The business rule does NOT re-evaluate STATUS. |
| COBOL Evidence | `STATUS` in SELECT (line 63); `HV-STATUS` in FETCH INTO (line 130); no business logic reads HV-STATUS. |
| Operator      | N/A (implicit: all fetched rows have STATUS = 'PENDING') |
| Input Fields  | STATUS from LEGACY.PAYMENT_QUEUE                   |
| Output/Result | Available in host variable but not used in decision logic. |
| Edge Cases    | If the cursor filter ever changed, the assumption that HV-STATUS = 'PENDING' would break. |
| Confidence    | HIGH — confirmed by both SQL filter and absence of HV-STATUS in any conditional. |

---

## BR-10 — CLOSE and COMMIT Errors Are Silently Ignored

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Rule ID       | BR-10                                              |
| Description   | The CLOSE and COMMIT SQL statements have no SQLCODE check following them. Any error they produce is silently discarded. |
| COBOL Evidence | Lines 100–106: CLOSE and COMMIT are executed, but there is no `IF SQLCODE` check after either statement. |
| Operator      | N/A — absence of check                             |
| Input Fields  | SQLCODE (after CLOSE and COMMIT) — not read        |
| Output/Result | Errors swallowed silently; no user notification.  |
| Edge Cases    | A COMMIT failure would cause the program to report success and display the processed count, but the data changes would not be persisted. |
| Confidence    | HIGH — no SQLCODE check exists in the source.      |

---

## Summary of Business Rules

| Rule ID | Short Description                            | Confidence |
|---------|----------------------------------------------|------------|
| BR-01   | Filter: only PENDING payments                | HIGH       |
| BR-02   | AMOUNT <= CREDIT_LIMIT → APPROVED            | HIGH       |
| BR-03   | AMOUNT > CREDIT_LIMIT → REVIEW               | HIGH       |
| BR-04   | Counter increments only on successful UPDATE | HIGH       |
| BR-05   | OPEN failure exits without COMMIT            | HIGH       |
| BR-06   | FETCH error terminates loop; batch committed | HIGH       |
| BR-07   | Single COMMIT at end of batch                | HIGH       |
| BR-08   | ACCOUNT_ID is part of fetched data interface | HIGH       |
| BR-09   | STATUS fetched but not re-evaluated          | HIGH       |
| BR-10   | CLOSE/COMMIT errors silently ignored         | HIGH       |
