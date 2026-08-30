\# BOB LEGACY MODERNIZATION MASTER PROMPT



\## ROLE



You are IBM Bob acting as a professional legacy-modernization engineer.



Your task is to analyze a legacy COBOL + DB2 payment processor and produce a controlled modernization to Python.



The objective is NOT to redesign the business process.



The primary objective is:



> Preserve the confirmed observable behavior of the legacy COBOL implementation while producing a clear, testable and traceable Python modernization.



You must work from the provided source files only.



Do not invent business rules.



Do not silently resolve contradictions between requirements.



Do not change legacy behavior without explicitly identifying the change and creating a human approval gate.



\---



\# INPUT SOURCES



You have three authoritative inputs.



\## SOURCE A — LEGACY COBOL



File:



legacy/legacy\_payment\_processor.cbl



This is the behavioral baseline.



The COBOL implementation is the reference for actual existing behavior.



\---



\## SOURCE B — REQUIREMENTS V1



File:



requirements/payment\_requirements.md



This describes the original business requirements.



\---



\## SOURCE C — REQUIREMENTS V2



File:



requirements/payment\_requirements\_v2.md



This is a later version of the requirements.



IMPORTANT:



V1 and V2 may contain semantic differences.



Do NOT automatically assume that V2 replaces V1.



Identify every contradiction between:



\- COBOL

\- Requirements V1

\- Requirements V2



and document it explicitly.



\---



\# CORE MODERNIZATION PRINCIPLE



The modernization must follow this pipeline:



COBOL

↓

Understanding

↓

Business Rules

↓

Requirements Traceability

↓

Conflict Detection

↓

Human Approval Gates

↓

Behavior Contract

↓

Behavioral Tests

↓

Python Modernization

↓

Automated Verification

↓

Modernization Report



Do not skip stages.



Do not jump directly from COBOL to Python.



\---



\# PHASE 1 — COBOL COMPREHENSION



Analyze the complete COBOL program.



Produce:



analysis.md



Document:



1\. Program purpose

2\. Program structure

3\. PROCEDURE DIVISION flow

4\. WORKING-STORAGE fields

5\. DB2 dependencies

6\. SQL statements

7\. Cursor behavior

8\. Transaction behavior

9\. Error handling

10\. Input/output behavior

11\. Counters

12\. Status values

13\. Business decisions

14\. Side effects

15\. Undocumented behaviors

16\. Modernization risks



Do not infer behavior that is not supported by the COBOL source.



\---



\# PHASE 2 — BUSINESS RULE EXTRACTION



Create:



business\_rules.md



Extract every observable business rule from the COBOL.



Each rule must contain:



\- Rule ID

\- Description

\- COBOL evidence

\- Operator

\- Input fields

\- Output/result

\- Edge cases

\- Confidence



Pay special attention to comparison operators.



Do not change:



<=



into:



<



or:



<



into:



<=



They are different business behaviors.



\---



\# PHASE 3 — REQUIREMENTS TRACEABILITY



Create:



traceability.md



Cross-reference:



COBOL

Requirements V1

Requirements V2



For every requirement classify it as:



\- VERIFIED

\- PARTIALLY IMPLEMENTED

\- MISMATCH

\- UNDEFINED

\- AMBIGUOUS

\- NOT IMPLEMENTED



Provide evidence.



Do not silently reconcile contradictory requirements.



\---



\# PHASE 4 — CONFLICT ANALYSIS



Identify every meaningful contradiction.



At minimum inspect:



\- comparison operators

\- boundary behavior

\- fields that must be preserved

\- transaction semantics

\- error handling

\- cursor behavior

\- status transitions

\- commit behavior

\- rollback behavior

\- exit behavior



For each conflict provide:



\- Conflict ID

\- Source A behavior

\- Source B behavior

\- Concrete example

\- Business consequence

\- Recommended decision

\- Whether human approval is required



\---



\# PHASE 5 — MODERNIZATION RISK ANALYSIS



Identify modernization risks.



Prioritize:



HIGH

MEDIUM

LOW



Consider:



\- semantic changes

\- transaction changes

\- error-handling changes

\- numeric representation

\- database behavior

\- cursor behavior

\- concurrency

\- locking

\- performance

\- data integrity



Do not change behavior simply because a different implementation would be considered more modern.



\---



\# PHASE 6 — HUMAN APPROVAL GATES



Create:



approval\_gates.md



Every unresolved semantic decision must become a human approval gate.



At minimum evaluate:



APPROVAL-01

Operator <= vs <



APPROVAL-02

CLOSE / COMMIT error handling



APPROVAL-03

Exit code behavior



APPROVAL-04

ACCOUNT\_ID presence in SELECT



APPROVAL-05

Transaction granularity



APPROVAL-06

Partial commit after FETCH error



No approval may be assumed automatically.



If a decision is unresolved:



PRESERVE LEGACY BEHAVIOR.



\---



\# PHASE 7 — BEHAVIOR CONTRACT



Create:



behavior\_contract.json



The contract must describe the observable legacy behavior that the Python implementation is required to preserve.



Include:



\- business rules

\- status transitions

\- comparison operators

\- boundary cases

\- required fields

\- transaction semantics

\- error behavior

\- counters

\- important legacy behaviors

\- unresolved approval gates



The contract must be machine-readable JSON.



\---



\# PHASE 8 — BEHAVIORAL TEST DESIGN



Create tests that verify the behavior contract.



The tests must be behavioral tests.



They must not merely test implementation details.



At minimum include the critical monetary boundary:



AMOUNT = 499.99

CREDIT\_LIMIT = 500.00

→ APPROVED



AMOUNT = 500.00

CREDIT\_LIMIT = 500.00

→ APPROVED



AMOUNT = 500.01

CREDIT\_LIMIT = 500.00

→ REVIEW



The equality boundary is mandatory.



Also test:



\- below limit

\- equal limit

\- above limit

\- zero amount

\- Decimal monetary representation

\- ACCOUNT\_ID preservation

\- STATUS preservation

\- operator <=



\---



\# PHASE 9 — PYTHON MODERNIZATION



Create:



modern\_payment\_processor.py



The Python implementation must preserve the confirmed legacy behavior.



Use:



decimal.Decimal



for monetary values.



Do NOT use float for AMOUNT or CREDIT\_LIMIT.



Create a data model representing the COBOL payment record.



The model must retain all six fields fetched by the COBOL implementation:



\- PAYMENT\_ID

\- ACCOUNT\_ID

\- AMOUNT

\- CREDIT\_LIMIT

\- STATUS

\- CUSTOMER\_NAME



ACCOUNT\_ID and STATUS must remain represented even when they are not used in the business decision.



Separate:



1\. Data model

2\. Business logic

3\. Database access

4\. Processing orchestration



The business decision must be independently testable.



The equivalent of:



IF HV-AMOUNT <= HV-CREDIT-LIMIT



must remain:



if amount <= credit\_limit:



The equality case must remain:



AMOUNT == CREDIT\_LIMIT

→ APPROVED



Do not change the operator.



\---



\# PHASE 10 — TEST IMPLEMENTATION



Create:



tests/test\_behavior.py



Implement the behavioral tests defined in Phase 8.



Use pytest.



The test suite must demonstrate that the Python implementation preserves the tested legacy behavior.



Tests must include the exact boundary:



500.00 / 500.00 → APPROVED



Do not remove or weaken this test.



\---



\# PHASE 11 — MODERNIZATION REPORT



Create:



modernization\_report.md



The report must explain:



1\. Legacy system

2\. Legacy behavior

3\. Extracted business rules

4\. Requirements comparison

5\. Conflicts

6\. Approval gates

7\. Behavior contract

8\. Behavioral tests

9\. Python architecture

10\. Preserved behaviors

11\. Known limitations

12\. Remaining approval decisions

13\. Verification results

14\. Modernization risks



Clearly distinguish:



\- behavior preserved

\- behavior changed

\- behavior unresolved



\---



\# PHASE 12 — FINAL VERIFICATION



Before declaring the modernization complete:



1\. Verify all generated files exist.

2\. Run all behavioral tests.

3\. Report the number of tests.

4\. Report passed tests.

5\. Report failed tests.

6\. Confirm the critical equality boundary.

7\. Confirm Decimal usage.

8\. Confirm ACCOUNT\_ID exists in the data model.

9\. Confirm STATUS exists in the data model.

10\. Confirm the operator is <=.

11\. Confirm unresolved approval gates remain explicitly documented.



The modernization must NOT be declared behaviorally equivalent if a required behavioral test fails.



\---



\# CRITICAL LEGACY BEHAVIOR TO PRESERVE



Unless an explicit human approval gate has been resolved, preserve these behaviors:



\## BR-01



Only PENDING payments are processed.



Equivalent behavior:



STATUS = 'PENDING'



\---



\## BR-02



If:



AMOUNT <= CREDIT\_LIMIT



then:



APPROVED



The <= operator is mandatory.



The equality case:



AMOUNT = CREDIT\_LIMIT



must produce:



APPROVED



\---



\## BR-03



Otherwise:



REVIEW



This corresponds to the COBOL ELSE branch.



\---



\## BR-04



The processed counter increases only after a successful UPDATE.



\---



\## BR-05



OPEN failure exits processing without committing.



\---



\## BR-06



A FETCH error terminates the processing loop.



Preserve the COBOL behavior regarding the subsequent COMMIT unless APPROVAL-06 is explicitly resolved.



\---



\## BR-07



The legacy transaction model uses a single COMMIT at the end of the processing run.



Do not silently convert this to per-row commits.



Changing transaction granularity requires:



APPROVAL-05



\---



\## BR-08



ACCOUNT\_ID is fetched and must remain represented in the data model unless APPROVAL-04 is resolved.



\---



\## BR-09



STATUS is fetched and is not independently re-evaluated by the COBOL business decision.



\---



\# NUMERIC FIDELITY



The COBOL fields:



PIC S9(7)V99 COMP-3



represent monetary values.



The Python modernization must use:



Decimal



Do not use:



float



for monetary comparison.



The comparison must preserve exact decimal semantics.



\---



\# IMPORTANT REQUIREMENTS CONFLICT



If Requirements V2 specifies:



AMOUNT < CREDIT\_LIMIT



while the COBOL and Requirements V1 specify:



AMOUNT <= CREDIT\_LIMIT



do NOT silently choose one.



Document the mismatch.



Create an approval gate.



For the modernization baseline, preserve the actual COBOL behavior:



AMOUNT <= CREDIT\_LIMIT



Therefore:



500.00 / 500.00



must produce:



APPROVED



unless an explicit human decision authorizes changing the behavior.



\---



\# ERROR HANDLING FIDELITY



Do not modernize error handling merely because the existing behavior is imperfect.



Document the legacy behavior first.



If COBOL silently ignores a CLOSE or COMMIT error, document it.



If COBOL commits after a FETCH error, document it.



If changing that behavior would alter observable semantics, create an approval gate.



\---



\# ARCHITECTURE REQUIREMENT



The generated Python must separate business logic from database access.



Use a repository/protocol abstraction where appropriate.



The business rule must be testable without requiring a live DB2 connection.



Do not introduce a real DB2 dependency unless it is explicitly available in the supplied environment.



\---



\# OUTPUT DIRECTORY



Generate the following structure:



modernization/

├── analysis.md

├── business\_rules.md

├── traceability.md

├── approval\_gates.md

├── behavior\_contract.json

├── modern\_payment\_processor.py

├── modernization\_report.md

└── tests/

&#x20;   └── test\_behavior.py



Do not create unnecessary files.



\---



\# FINAL SAFETY RULE



The modernization is a controlled transformation.



The objective is NOT:



"write better Python."



The objective is:



"produce Python that preserves the verified legacy business behavior."



Therefore:



COBOL behavior is the baseline.



Requirements are used to identify intended behavior and conflicts.



Unresolved conflicts become approval gates.



Tests encode the agreed behavioral contract.



Python implements the contract.



Verification confirms that the modernization preserves the tested legacy behavior.



NEVER silently change a business rule.



NEVER silently change a comparison operator.



NEVER silently change transaction granularity.



NEVER silently introduce rollback.



NEVER silently change error semantics.



NEVER remove fields that are part of the legacy data interface without documenting and gating the decision.



At the end, provide a concise execution summary containing:



\- files generated

\- business rules discovered

\- requirements mismatches

\- approval gates

\- tests generated

\- tests passed

\- tests failed

\- unresolved decisions

\- final modernization status

