# Process notes: what went wrong

Moved out of the write-up to keep Deliverable C inside its two-to-four page
limit. It is kept because the commit history shows it anyway, and because
the failure modes are more instructive than the successes.

Included because the repository's commit history shows it anyway, and because
the failure mode is more interesting than the successes.

**I extrapolated wall-clock time from token volume** and started the most
expensive run of the project on that estimate. Judge scoring was serial — 114
calls per matrix cell, each waiting on a model that reasons before answering —
and the run wrote nothing to disk until the end. It was stopped after four hours
without completing one of four combinations, and it left nothing behind.
`docs/02-metrics.md` says in as many words that cost and performance are
measured and never extrapolated. I wrote that rule, quoted it while reviewing
other work in this repository, and then broke it.

A ten-minute pilot afterwards found three defects the four hours had not.

**"Persist as you go" had to be learned three times** — in the dataset
generator, in a top-up script, and finally in the matrix — despite being fixed
in the first two before the third was written.

**Several defects were invisible to a green test suite**: the refusal branch
never fired for any judged metric because GEval renames itself, and the tests
checked a constant against itself rather than against a real metric's name; the
draft stage could not recover from a single malformed response because a
capture used `dict.setdefault`, and 238 tests passed on either side of that bug.

The pattern in all of these is the same, and it is the one this project was
supposed to be about: **a test that does not go through the real entry point
does not test anything.** The verification passes in this repository found real
defects precisely when they stopped reading the code and started running it.
