# Repair 2 decision

Status: `READY_FOR_REVIEW`

Repair 2 closes only the fixed 2 P1 + 1 P2 scope:

- terminal-loss keeps honest `BLOCKED/1` accounting and is never auto-resendable;
- current schema v2 rejects legacy aliases and every non-positive/non-integer/missing PID;
- strict replay support derives from the complete legal state table and real required controls, with terminal-loss、legacy alias、PID domain each proven capable of downgrading the matrix cell.

No production pipeline、outbox、runner、transport、operation、app、article、registry、metadata or publishing file was changed. No Gemini、HTTP、external model、credential、retry、dependency、merge、push、deploy、publish or content recovery was used.

This is Repair 2/2. Return the candidate to the original Reviewer for final independent re-review. The repair author does not certify `GO`. If that review remains `NO_GO`, chain `CONTENT-GEMINI-REVIEWER-V4-001` is `BLOCKED`; Repair 3 is forbidden.
