       IDENTIFICATION DIVISION.
       PROGRAM-ID. LEGACY-PAYMENT-PROCESSOR.
       AUTHOR. BRIDGE-GUARD-DEMO-TEAM.
       DATE-WRITTEN. 2026-08-28.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.

           EXEC SQL
               INCLUDE SQLCA
           END-EXEC.

      *------------------------------------------------------------*
      * PAYMENT DATABASE RECORD                                    *
      *------------------------------------------------------------*

       01  PAYMENT-RECORD.
           05  HV-PAYMENT-ID       PIC S9(9) COMP.
           05  HV-ACCOUNT-ID       PIC S9(9) COMP.
           05  HV-AMOUNT           PIC S9(7)V99 COMP-3.
           05  HV-CREDIT-LIMIT     PIC S9(7)V99 COMP-3.
           05  HV-STATUS           PIC X(10).
           05  HV-CUSTOMER-NAME    PIC X(40).

      *------------------------------------------------------------*
      * PROCESSING FLAGS AND CONSTANTS                             *
      *------------------------------------------------------------*

       01  WS-EOF-FLAG             PIC X VALUE 'N'.

           88  END-OF-DATA         VALUE 'Y'.

       01  WS-PENDING              PIC X(10)
                                    VALUE 'PENDING'.

       01  WS-APPROVED             PIC X(10)
                                    VALUE 'APPROVED'.

       01  WS-REVIEW               PIC X(10)
                                    VALUE 'REVIEW'.

       01  WS-PROCESSED-COUNT      PIC 9(7)
                                    VALUE ZERO.

       01  WS-DISPLAY-AMOUNT       PIC $$$,$$$,$$9.99.

       01  WS-DISPLAY-LIMIT        PIC $$$,$$$,$$9.99.

      *------------------------------------------------------------*
      * DB2 CURSOR                                                 *
      *------------------------------------------------------------*

           EXEC SQL
               DECLARE PAYMENT-CURSOR CURSOR FOR
                   SELECT
                       PAYMENT_ID,
                       ACCOUNT_ID,
                       AMOUNT,
                       CREDIT_LIMIT,
                       STATUS,
                       CUSTOMER_NAME
                   FROM LEGACY.PAYMENT_QUEUE
                   WHERE STATUS = :WS-PENDING
                   FOR UPDATE OF STATUS
           END-EXEC.

      *------------------------------------------------------------*
      * MAIN PROGRAM                                               *
      *------------------------------------------------------------*

       PROCEDURE DIVISION.

       0000-MAIN.

           DISPLAY
               "--------------------------------------------".

           DISPLAY
               " LEGACY PAYMENT PROCESSOR".

           DISPLAY
               "--------------------------------------------".

           EXEC SQL
               OPEN PAYMENT-CURSOR
           END-EXEC.

           IF SQLCODE NOT = 0
               DISPLAY "ERROR OPENING PAYMENT CURSOR"
               DISPLAY "SQLCODE: " SQLCODE
               GOBACK
           END-IF.

           PERFORM 1000-PROCESS-PAYMENTS
               UNTIL END-OF-DATA.

           EXEC SQL
               CLOSE PAYMENT-CURSOR
           END-EXEC.

           EXEC SQL
               COMMIT
           END-EXEC.

           DISPLAY
               "PAYMENTS PROCESSED: "
               WS-PROCESSED-COUNT.

           DISPLAY
               "PROCESS COMPLETE.".

           GOBACK.

      *------------------------------------------------------------*
      * FETCH PAYMENT                                              *
      *------------------------------------------------------------*

       1000-PROCESS-PAYMENTS.

           EXEC SQL
               FETCH PAYMENT-CURSOR
               INTO
                   :HV-PAYMENT-ID,
                   :HV-ACCOUNT-ID,
                   :HV-AMOUNT,
                   :HV-CREDIT-LIMIT,
                   :HV-STATUS,
                   :HV-CUSTOMER-NAME
           END-EXEC.

           EVALUATE SQLCODE

               WHEN 100
                   SET END-OF-DATA TO TRUE

               WHEN 0
                   PERFORM 2000-PROCESS-PAYMENT

               WHEN OTHER
                   DISPLAY
                       "CRITICAL DB2 ERROR: "
                       SQLCODE
                   SET END-OF-DATA TO TRUE

           END-EVALUATE.

      *------------------------------------------------------------*
      * BUSINESS PROCESSING                                        *
      *------------------------------------------------------------*

       2000-PROCESS-PAYMENT.

           MOVE HV-AMOUNT
               TO WS-DISPLAY-AMOUNT.

           MOVE HV-CREDIT-LIMIT
               TO WS-DISPLAY-LIMIT.

           DISPLAY
               "PAYMENT ID: "
               HV-PAYMENT-ID.

           DISPLAY
               "CUSTOMER: "
               HV-CUSTOMER-NAME.

           DISPLAY
               "AMOUNT: "
               WS-DISPLAY-AMOUNT.

           DISPLAY
               "CREDIT LIMIT: "
               WS-DISPLAY-LIMIT.

      *------------------------------------------------------------*
      * BUSINESS RULE                                             *
      *------------------------------------------------------------*

           IF HV-AMOUNT <= HV-CREDIT-LIMIT

               EXEC SQL
                   UPDATE LEGACY.PAYMENT_QUEUE
                      SET STATUS = :WS-APPROVED
                    WHERE CURRENT OF PAYMENT-CURSOR
               END-EXEC

           ELSE

               EXEC SQL
                   UPDATE LEGACY.PAYMENT_QUEUE
                      SET STATUS = :WS-REVIEW
                    WHERE CURRENT OF PAYMENT-CURSOR
               END-EXEC

           END-IF.

      *------------------------------------------------------------*
      * UPDATE RESULT                                              *
      *------------------------------------------------------------*

           IF SQLCODE NOT = 0

               DISPLAY
                   "ERROR UPDATING PAYMENT: "
                   HV-PAYMENT-ID

               DISPLAY
                   "SQLCODE: "
                   SQLCODE

           ELSE

               ADD 1 TO WS-PROCESSED-COUNT

               DISPLAY
                   "PAYMENT STATUS UPDATED."

           END-IF.