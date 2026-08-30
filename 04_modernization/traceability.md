# Phase 3 — Requirements Traceability

**Sources:**  
- SOURCE A: `01_legacy/legacy_payment_processor.cbl` (behavioral baseline)  
- SOURCE B: `02_requirements/payment_requirements.md` (Requirements V1)  
- SOURCE C: `02_requirements/payment_requirements_v2.md` (Requirements V2)  

---

## Classification Key

| Status              | Meaning                                                         |
|---------------------|-----------------------------------------------------------------|
| VERIFIED            | COBOL behavior exactly matches the requirement                  |
| PARTIALLY IMPLEMENTED | Requirement partially matches COBOL                           |
| MISMATCH            | Requirement contradicts COBOL behavior                         |
| AMBIGUOUS           | Requirement is unclear or multiple interpretations exist        |
| UNDEFINED           | Requirement covers something not present in COBOL               |
| NOT IMPLEMENTED     | Requirement is absent from COBOL                               |

---

## Requirements V1 Traceability

### V1-REQ-01 — Only PENDING Payments Are Processed

> *"Only payments with status `PENDING` must be processed."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **VERIFIED**                                                    |
| COBOL Evidence | Cursor WHERE clause: `WHERE STATUS = :WS-PENDING` (line 66). |
| Notes       | Exact match. WS-PENDING = 'PENDING'. Only PENDING rows are fetched. |

---

### V1-REQ-02 — APPROVED When Amount ≤ Credit Limit

> *"A payment must be marked `APPROVED` when the payment amount is **less than or equal to** the account credit limit."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **VERIFIED**                                                    |
| COBOL Evidence | `IF HV-AMOUNT <= HV-CREDIT-LIMIT` (line 182); UPDATE to APPROVED. |
| Notes       | V1 uses "less than or equal to" — matches COBOL `<=` operator exactly. |

---

### V1-REQ-03 — REVIEW When Amount > Credit Limit

> *"A payment must be marked `REVIEW` when the payment amount is greater than the account credit limit."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **VERIFIED**                                                    |
| COBOL Evidence | ELSE branch of `IF HV-AMOUNT <= HV-CREDIT-LIMIT` (line 190); UPDATE to REVIEW. |
| Notes       | Consistent with `<=` operator — only triggers when AMOUNT > CREDIT_LIMIT. |

---

### V1-REQ-04 — All Fields Must Be Preserved

> *"Every processed payment must preserve its original payment identifier, account identifier, amount, credit limit, customer name, and processing status."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **PARTIALLY IMPLEMENTED**                                       |
| COBOL Evidence | All 6 fields are fetched. Only STATUS is updated (to APPROVED/REVIEW). PAYMENT_ID, ACCOUNT_ID, AMOUNT, CREDIT_LIMIT, CUSTOMER_NAME are read but not modified. |
| Notes       | The fields are technically preserved in the sense that non-STATUS fields are not overwritten. However, "processing status" is intentionally changed (PENDING → APPROVED/REVIEW). The requirement's phrasing "preserve ... processing status" is ambiguous: if it means preserve the STATUS column value, it contradicts the program's purpose. More likely it means preserve the record association. Classified PARTIALLY IMPLEMENTED because ACCOUNT_ID is fetched but never displayed or confirmed in output. |

---

### V1-REQ-05 — Database Errors Must Not Be Silently Ignored

> *"A database error must not be silently ignored."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **PARTIALLY IMPLEMENTED**                                       |
| COBOL Evidence | OPEN error: checked and reported (lines 91–95). FETCH error: reported to DISPLAY (lines 143–146). UPDATE error: reported to DISPLAY (lines 206–212). CLOSE error: **NOT checked — silently ignored**. COMMIT error: **NOT checked — silently ignored**. |
| Notes       | V1-REQ-05 is violated by the legacy COBOL itself: CLOSE and COMMIT errors are silently ignored (BR-10). This is a known undocumented behavior of the COBOL. The requirement cannot be classified VERIFIED when CLOSE/COMMIT errors go undetected. |

---

## Requirements V2 Traceability

### V2-REQ-01 — Only PENDING Payments Are Processed

> *"Only payments with status `PENDING` must be processed."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **VERIFIED**                                                    |
| COBOL Evidence | Same as V1-REQ-01. No change.                                 |
| Notes       | V2 and V1 are identical on this requirement.                   |

---

### V2-REQ-02 — APPROVED When Amount < Credit Limit ⚠️ CONFLICT

> *"A payment must be marked `APPROVED` when the payment amount is **less than** the account credit limit."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **MISMATCH**                                                    |
| COBOL Evidence | `IF HV-AMOUNT <= HV-CREDIT-LIMIT` (line 182) — operator is `<=`. |
| V1 Evidence | V1-REQ-02 says "less than or equal to" — matches COBOL.        |
| Conflict    | **V2 uses `<` (strict less-than). COBOL uses `<=`. V1 uses `<=`.** |
| Business Impact | Under V2, when AMOUNT = CREDIT_LIMIT exactly (e.g., $500.00 vs $500.00 limit), the payment would be REVIEW. Under COBOL/V1, it would be APPROVED. |
| Concrete Example | AMOUNT = 500.00, CREDIT_LIMIT = 500.00 → COBOL: APPROVED; V2: REVIEW |
| Decision Required | **APPROVAL-01 — see approval_gates.md** |

---

### V2-REQ-03 — REVIEW When Amount > Credit Limit

> *"A payment must be marked `REVIEW` when the payment amount is greater than the account credit limit."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **VERIFIED** (consistent with COBOL given V2-REQ-02 conflict)  |
| COBOL Evidence | ELSE branch — UPDATE to REVIEW.                              |
| Notes       | If V2-REQ-02 uses `<`, then this requirement leaves the equality case (AMOUNT = CREDIT_LIMIT) unspecified in V2. Under V2 logic, the equality case falls to REVIEW by default (since it fails the `<` condition). But this conflicts with COBOL. The equality boundary behavior remains an unresolved conflict. |

---

### V2-REQ-04 — All Fields Must Be Preserved

> *"Every processed payment must preserve its original payment identifier, account identifier, amount, credit limit, customer name, and processing status."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **PARTIALLY IMPLEMENTED**                                       |
| Notes       | Identical to V1-REQ-04. Same analysis applies.                 |

---

### V2-REQ-05 — Database Errors Must Not Be Silently Ignored

> *"A database error must not be silently ignored."*

| Field       | Value                                                           |
|-------------|-----------------------------------------------------------------|
| Status      | **PARTIALLY IMPLEMENTED**                                       |
| Notes       | Identical to V1-REQ-05. CLOSE and COMMIT errors are silently ignored in COBOL. |

---

## Traceability Summary

| Req ID   | Source | Description                           | Status                    |
|----------|--------|---------------------------------------|---------------------------|
| V1-REQ-01 | V1    | Only PENDING processed                | VERIFIED                  |
| V1-REQ-02 | V1    | APPROVED when amount <= limit         | VERIFIED                  |
| V1-REQ-03 | V1    | REVIEW when amount > limit            | VERIFIED                  |
| V1-REQ-04 | V1    | All fields preserved                  | PARTIALLY IMPLEMENTED     |
| V1-REQ-05 | V1    | DB errors not silently ignored        | PARTIALLY IMPLEMENTED     |
| V2-REQ-01 | V2    | Only PENDING processed                | VERIFIED                  |
| V2-REQ-02 | V2    | APPROVED when amount < limit          | **MISMATCH** ⚠️           |
| V2-REQ-03 | V2    | REVIEW when amount > limit            | VERIFIED (with conflict)  |
| V2-REQ-04 | V2    | All fields preserved                  | PARTIALLY IMPLEMENTED     |
| V2-REQ-05 | V2    | DB errors not silently ignored        | PARTIALLY IMPLEMENTED     |

---

## Detected Semantic Contradictions

### CONTRADICTION-01 — Comparison Operator (`<=` vs `<`)

| Field        | Value                                              |
|--------------|----------------------------------------------------|
| COBOL        | `IF HV-AMOUNT <= HV-CREDIT-LIMIT` (line 182)      |
| V1           | "less than or equal to" → `<=`                    |
| V2           | "less than" → `<`                                 |
| Impact       | Equality boundary: AMOUNT = CREDIT_LIMIT → APPROVED (COBOL/V1) vs REVIEW (V2) |
| Resolution   | **NOT auto-resolved. See APPROVAL-01.**            |

### CONTRADICTION-02 — Silent DB Error Tolerance

| Field        | Value                                              |
|--------------|----------------------------------------------------|
| COBOL        | CLOSE and COMMIT errors are silently ignored (BR-10) |
| V1 + V2      | "A database error must not be silently ignored"    |
| Impact       | A COMMIT failure leaves data uncommitted while the program reports success |
| Resolution   | **NOT auto-resolved. See APPROVAL-02.**            |
