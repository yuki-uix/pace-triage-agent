# Extras — outside the assessed deliverable

Nothing in this directory is part of Deliverables A, B or C. It is kept because
it was built and works, and deleting working code to tidy a submission hides
what actually happened. It is separated because it should not be read as part of
the engineering the case study asks to be judged on.

## `web-demo/`

A local web interface and a zero-dependency Vercel Function that make the frozen
assignment demo clickable for a non-technical reader.

**Why it is here rather than in the main line.** `docs/04-scope.md` rejected a
web UI at the outset, on the grounds that the brief permits a CLI and a UI
consumes hours while demonstrating nothing being assessed. That reasoning still
holds for the *assessment*; the demo was built afterwards for communication, and
leaving it in the main line would have left the repository contradicting its own
scope document.

**One real risk it carries.** `api/index.mjs` re-implements the triage and draft
system prompts in JavaScript. The injection-resistance metric extracts its
leakage probes from the Python constants in `src/pipeline.py` at call time, so
that copy is *not* covered: if the Python prompt changes, the JavaScript one
silently drifts and nothing fails. Treat the hosted demo as illustrative of an
older prompt unless the copy has been re-checked by hand.

Run it locally:

```bash
.venv/bin/python extras/web-demo/web_demo.py
```

Its tests run with the rest of the suite (`pytest extras/`), because code that
is kept should stay working.
