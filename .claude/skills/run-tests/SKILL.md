---
description: Run pytest. With no arguments runs full suite; pass a file path or `file::test` to narrow scope.
argument-hint: [path or test-id]
---

!`.venv/Scripts/python.exe -m pytest $ARGUMENTS -q`

Report pass/fail counts and any tracebacks verbatim. If a test fails, do not attempt a fix unless I ask.
