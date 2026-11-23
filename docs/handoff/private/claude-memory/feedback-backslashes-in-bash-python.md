---
name: feedback-backslashes-in-bash-python
description: "Writing files that contain backslashes through a python heredoc in the Bash tool silently halves them; use Write or Edit for Dockerfile continuations, regexes and sed back references"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-06T10:51:48.980Z
---

In this environment a `\\` typed inside a Bash tool command reaches the shell as a single `\`. Python edits that put a Dockerfile line continuation (`\\` then newline) or a sed back reference (`\\1`) into a file therefore lose them: the continuation lines join into one, and `\1` becomes the control character 0x01 (it displays as nothing). This produced a Dockerfile RUN step that built fine and did the wrong thing (CSP origin empty) until a rendered check caught it (2026-10-06, website demo page).

**Why:** the failure is silent and the file looks plausible in a Read.

**How to apply:** put any text that needs a literal backslash in a file with the Write tool (it is verbatim) or change it with Edit; if Python must do the splice, have it read the new text from a file written by Write. After such an edit, grep the file for stray control characters and verify the behaviour (build, run, curl) instead of trusting the text. Related: [[verity-website-deploy]].
