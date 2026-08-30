# Phase 1 — COBOL Comprehension Analysis

**Program:** `LEGACY-PAYMENT-PROCESSOR`  
**Author:** BRIDGE-GUARD-DEMO-TEAM  
**Date Written:** 2026-08-28  
**Source File:** `01_legacy/legacy_payment_processor.cbl`

---

## 1. Program Purpose

This program is a batch payment processor. It opens a DB2 cursor over a table
of pending payment records, evaluates each record against a credit-limit rule,
updates the record status to either `APPROVED` or `REVIEW`, and at the end
commits all changes in a single transaction.

---

## 2. Program Structure

| Division / Section    | Content                                                      |
|-----------------------|--------------------------------------------------------------|
| IDENTIFICATION        | Program name, author, date                                   |
| ENVIRONMENT           | CONFIGURATION SECTION (empty — no FILE-CONTROL)              |
| DATA / WORKING-STORAGE | SQLCA include, PAYMENT-RECORD host variables, flags, constants, display fields |
| PROCEDURE DIVISION    | 0000-MAIN, 1000-PROCESS-PAYMENTS, 2000-PROCESS-PAYMENT       |

---

## 3. PROCEDURE DIVISION Flow

```
0000-MAIN
  │
  ├─ DISPLAY header banner
  ├─ OPEN PAYMENT-CURSOR
  │     └─ IF SQLCODE ≠ 0 → DISPLAY error + GOBACK   (exits without COMMIT)
  │
  ├─ PERFORM 1000-PROCESS-PAYMENTS UNTIL END-OF-DATA
  │     │
  │     └─ 1000-PROCESS-PAYMENTS
  │           ├─ FETCH PAYMENT-CURSOR INTO host variables
  │           └─ EVALUATE SQLCODE
  │                 WHEN 100  → SET END-OF-DATA = TRUE
  │                 WHEN 0    → PERFORM 2000-PROCESS-PAYMENT
  │                 WHEN OTHER→ DISPLAY critical error + SET END-OF-DATA = TRUE
  │
  │           └─ 2000-PROCESS-PAYMENT
  │                 ├─ MOVE amounts to display fields
  │                 ├─ DISPLAY payment details
  │                 ├─ IF HV-AMOUNT <= HV-CREDIT-LIMIT
  │                 │     UPDATE STATUS = 'APPROVED'  WHERE CURRENT OF CURSOR
  │                 │   ELSE
  │                 │     UPDATE STATUS = 'REVIEW'    WHERE CURRENT OF CURSOR
  │                 ├─ IF SQLCODE ≠ 0 → DISPLAY update error (no abort, no rollback)
  │                 └─ ELSE → ADD 1 TO WS-PROCESSED-COUNT + DISPLAY confirmation
  │
  ├─ CLOSE PAYMENT-CURSOR       (SQLCODE result is NOT checked — silently ignored)
  ├─ COMMIT                     (SQLCODE result is NOT checked — silently ignored)
  ├─ DISPLAY "PAYMENTS PROCESSED: " WS-PROCESSED-COUNT
  └─ GOBACK
```

---

## 4. WORKING-STORAGE Fields

| Field                 | Picture          | Notes                                       |
|-----------------------|------------------|---------------------------------------------|
| HV-PAYMENT-ID         | PIC S9(9) COMP   | Host variable — payment primary key         |
| HV-ACCOUNT-ID         | PIC S9(9) COMP   | Host variable — account identifier (fetched, not used in business logic) |
| HV-AMOUNT             | PIC S9(7)V99 COMP-3 | Monetary amount — packed decimal, 2 decimal places |
| HV-CREDIT-LIMIT       | PIC S9(7)V99 COMP-3 | Credit limit — packed decimal, 2 decimal places |
| HV-STATUS             | PIC X(10)        | Payment status string                       |
| HV-CUSTOMER-NAME      | PIC X(40)        | Customer name string                        |
| WS-EOF-FLAG           | PIC X VALUE 'N'  | Loop control; 88 level END-OF-DATA = 'Y'    |
| WS-PENDING            | PIC X(10) VALUE 'PENDING'  | Constant used in cursor WHERE clause and host variable comparison |
| WS-APPROVED           | PIC X(10) VALUE 'APPROVED' | Constant used in UPDATE SET                |
| WS-REVIEW             | PIC X(10) VALUE 'REVIEW'   | Constant used in UPDATE SET                |
| WS-PROCESSED-COUNT    | PIC 9(7) VALUE ZERO        | Counts successful UPDATEs                  |
| WS-DISPLAY-AMOUNT     | PIC $$$,$$$,$$9.99         | Formatted display field (display only)     |
| WS-DISPLAY-LIMIT      | PIC $$$,$$$,$$9.99         | Formatted display field (display only)     |

---

## 5. DB2 Dependencies

- **Table:** `LEGACY.PAYMENT_QUEUE`
- **Schema:** `LEGACY`
- **Cursor:** `PAYMENT-CURSOR` — declared in WORKING-STORAGE
- **SQLCA:** Standard DB2 SQL Communication Area (included via INCLUDE SQLCA)
- **SQLCODE field** checked at: OPEN, FETCH, UPDATE
- **SQLCODE field NOT checked** at: CLOSE, COMMIT

---

## 6. SQL Statements

| Statement     | Location           | Description                                                           |
|---------------|--------------------|-----------------------------------------------------------------------|
| DECLARE CURSOR | WORKING-STORAGE   | Selects 6 columns WHERE STATUS = 'PENDING', FOR UPDATE OF STATUS      |
| OPEN           | 0000-MAIN          | Opens cursor; SQLCODE checked immediately                            |
| FETCH          | 1000-PROCESS-PAYMENTS | Reads one row per call into host variables                        |
| UPDATE (×2)    | 2000-PROCESS-PAYMENT | Positional UPDATE via `WHERE CURRENT OF PAYMENT-CURSOR`             |
| CLOSE          | 0000-MAIN (post-loop) | SQLCODE NOT checked                                               |
| COMMIT         | 0000-MAIN (post-close) | SQLCODE NOT checked; single commit for entire batch              |

---

## 7. Cursor Behavior

- **Cursor type:** Read-only scan with `FOR UPDATE OF STATUS` lock intent.
- **Filter:** Only rows where `STATUS = 'PENDING'` are included.
- **Fetch style:** One row per PERFORM iteration.
- **End-of-set:** SQLCODE 100 signals no more rows; sets END-OF-DATA flag.
- **Error on FETCH:** Non-zero, non-100 SQLCODE sets END-OF-DATA flag; no ROLLBACK is performed.
- **Update scope:** `WHERE CURRENT OF PAYMENT-CURSOR` — each UPDATE targets the currently fetched row exactly.

---

## 8. Transaction Behavior

- **Granularity:** Single transaction spanning all processed rows.
- **Commit point:** One COMMIT at the end of the processing run, after CLOSE.
- **No ROLLBACK statement** exists anywhere in the program.
- **OPEN failure:** GOBACK without COMMIT (implicitly no commit for that run).
- **FETCH error:** Sets END-OF-DATA; loop ends; proceeds to CLOSE → COMMIT. Rows already updated ARE committed.
- **UPDATE error:** Logged to DISPLAY; processing continues to next row; counter NOT incremented for failed update.

---

## 9. Error Handling

| Error Scenario              | COBOL Behavior                                      |
|-----------------------------|-----------------------------------------------------|
| OPEN cursor fails           | DISPLAY error + SQLCODE, then GOBACK (exits immediately, no commit) |
| FETCH returns SQLCODE 100   | Normal end-of-data; sets EOF flag, exits loop cleanly |
| FETCH returns non-0, non-100| DISPLAY critical error + SQLCODE; sets EOF flag; DOES NOT rollback; proceeds to CLOSE+COMMIT |
| UPDATE fails (SQLCODE ≠ 0)  | DISPLAY error message + SQLCODE; continues to next payment; counter not incremented |
| CLOSE fails                 | Silently ignored (SQLCODE not checked)              |
| COMMIT fails                | Silently ignored (SQLCODE not checked)              |

---

## 10. Input/Output Behavior

**Input:** DB2 table `LEGACY.PAYMENT_QUEUE`, rows where STATUS = 'PENDING'  
**Output:**  
- DB2 STATUS field updated to 'APPROVED' or 'REVIEW' per business rule  
- DISPLAY to SYSOUT: header banner, per-payment detail, update result, final count  

---

## 11. Counters

| Counter               | Increment Condition                                        |
|-----------------------|------------------------------------------------------------|
| WS-PROCESSED-COUNT    | Only when UPDATE SQLCODE = 0 (successful update). Not incremented on UPDATE failure. |

---

## 12. Status Values

| Value     | Meaning                                             |
|-----------|-----------------------------------------------------|
| PENDING   | Input state — only these rows are fetched           |
| APPROVED  | Output state — AMOUNT <= CREDIT_LIMIT               |
| REVIEW    | Output state — AMOUNT > CREDIT_LIMIT                |

---

## 13. Business Decisions

| Decision Point                     | Operator | Behavior                                 |
|------------------------------------|----------|------------------------------------------|
| AMOUNT vs CREDIT_LIMIT comparison  | `<=`     | AMOUNT <= CREDIT_LIMIT → APPROVED; else REVIEW |

**Critical detail:** The operator is `<=` (less-than-or-equal). This means that
when `AMOUNT == CREDIT_LIMIT`, the result is `APPROVED`, not `REVIEW`.

---

## 14. Side Effects

- DB2 rows are permanently modified (STATUS field updated) when COMMIT executes.
- Console DISPLAY output is produced for every payment (informational, not transactional).
- WS-PROCESSED-COUNT is a program-local counter; it is displayed but not persisted to DB2.

---

## 15. Undocumented Behaviors

| # | Observation                                                                           |
|---|---------------------------------------------------------------------------------------|
| U1 | CLOSE error is silently ignored — no error message, no SQLCODE check after CLOSE.   |
| U2 | COMMIT error is silently ignored — no error message, no SQLCODE check after COMMIT.  |
| U3 | When a FETCH error occurs, rows already updated in the batch ARE committed (no rollback). |
| U4 | HV-ACCOUNT-ID is fetched and stored in WORKING-STORAGE but is never used in any business decision or DISPLAY statement. |
| U5 | HV-STATUS is fetched (always 'PENDING' due to WHERE clause) but is not used or displayed in the output. |
| U6 | No ROLLBACK statement exists in the program. There is no error recovery path.         |
| U7 | The program always exits via GOBACK — normal and error exits use the same statement.  |

---

## 16. Modernization Risks

| Risk ID | Risk Description                                                                             | Priority |
|---------|----------------------------------------------------------------------------------------------|----------|
| R-01    | Operator `<=` vs `<` — V2 requirements specify `<`; silent change would break equality boundary | HIGH   |
| R-02    | Transaction granularity — converting single-COMMIT to per-row commits changes rollback semantics | HIGH  |
| R-03    | CLOSE/COMMIT error silently ignored — modernization may expose previously hidden failures     | MEDIUM   |
| R-04    | FETCH error → partial commit — modernization may introduce rollback not in legacy behavior    | HIGH     |
| R-05    | Packed decimal (COMP-3) monetary values — must use Decimal, not float, in Python             | HIGH     |
| R-06    | ACCOUNT_ID in data model — must not be silently dropped                                      | MEDIUM   |
| R-07    | DB2 dependency — Python must abstract DB layer; tests must not require live DB2 connection    | MEDIUM   |
| R-08    | No ROLLBACK in legacy — introducing rollback would be a silent semantic change               | HIGH     |
