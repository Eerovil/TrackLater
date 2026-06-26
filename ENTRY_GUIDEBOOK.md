# Time-Entry Reconstruction Guidebook

A method for rebuilding manual billing time entries (the kind you export to a time
tracker) from two signals you already produce: **git commits** and an
**ActivityWatch**-style activity log. Ordered by leverage — the early rules fix the
most errors. Goal: a draft close enough to confirm with light edits, not rewrite.

This file is the **generic method**. All names of clients, projects, repos, and the
title vocabulary live in your own config and in an optional, gitignored
`ENTRY_GUIDEBOOK.local.md` — never hardcode them here.

> **Scope**: you can only reconstruct days that have source data (commits / activity
> log). The method is tuned and measured on *derivable* days — those where billed
> time actually correlates with the signal. Days dominated by untracked work
> (meetings, offline, leave) or deliberate under/over-billing need human judgement
> and are out of scope for scoring (§6).

---

## 0. Mental model

- **git = WHAT** — which client/project, and the theme of the work. Most reliable.
- **activity log = WHEN** — session start/stop boundaries. Reliable for timing,
  noisy for *which* project (it classifies by window-title keywords).
- **Two layers: CLIENT then PROJECT.** Several projects can roll up to one billing
  client. The client is what the invoice cares about; pick it first (very robust),
  then the project within it.
- **A sub-project is often billed as its parent.** When you don't bother selecting
  the precise component, the work lands on the parent project. Confusing two
  projects *inside the same client* is cheap; confusing two clients is expensive.
- **The entry is a billing decision, not a measurement.** You bill a curated subset
  of real activity in clean rounded blocks. Some billed work leaves no digital
  trace (meetings, review, planning); some heavily-tracked work isn't billed.

All source timestamps are usually UTC; entries are local. Convert before comparing.

---

## 0b. Source-of-truth maps — LOAD FROM CONFIG, never hardcode

Read these from your tracker config (do not bake names into this file):

- **group → client**: which projects share one billing client (the invoice unit).
- **group → repos**: which git repositories map to which project/group.
- **group → activity-log keywords**: how the activity log auto-classifies window
  titles. Knowing this explains *why* the log is noisy — and why git, not the log,
  should decide the project.
- **group → valid projects**: the allowed `project` values per group, so generated
  entries only use real project names.

---

## 1. Output shape

- A handful of entries/day (often ~3), each a different client/project.
- Blocks are **contiguous, non-overlapping**, snapped to **:00 / :30**.
- Block length typically 0.5–4 h.
- **Daily total rounds to a whole/half hour.**
- Fields: `group`, `project = group:ProjectName`, `title` (epic label, §4),
  local `start`/`end`.

---

## 2. Day start & end

- **First block start = first meaningful activity, rounded to the nearest :30**
  (usually down). A fixed default start (e.g. the start of your workday) is a fine
  fallback.
- Build forward. Mid-day gaps are allowed (drop non-billable lulls), but keep
  blocks back-to-back unless the log shows a clear multi-hour gap.

---

## 2b. Billable HOURS model

**Never compute activity time by summing event durations.** Real working time is
*continuous and bridges short pauses*; it only stops at a real AFK gap. Compute it
as **bridged sessions**:

1. Use **classified (work-grouped) events only** — never unclassified ones (those
   include leisure apps and would inflate the total).
2. Sort by time; **merge any two events whose gap ≤ the AFK threshold** (commonly
   ~15 min — match your tracker's idle setting). A larger gap is real AFK and closes
   the session.
3. Working time = sum of the merged session spans (bridged gaps count as work).

Then apply the **billable window** (in local time), which encodes personal billing
habits — adjust the factors to your own:

- **Weekday daytime: bill in full.**
- **Evening: bill at a reduced factor** (e.g. ~15%) if evening work is usually
  optional/"fun" rather than required.
- **Weekend: bill ≈ 0 unless it's important/required work** (e.g. an incident).

Then **split the day's hours across the selected clients by commit share** and round
each block to :30. (Commit share predicts the split better than activity share.)

---

## 3. Which projects to bill (selection)

### 3a. FIRST: fold each sub-project into its parent
Using the client map (§0b), before counting: if a sub-project had only a few
commits that day, **add its commits/activity to its parent project and drop it**.
Keep a sub-project as its own entry only on a *dedicated* day for it — operationally,
when its commit count crosses a high threshold (tune per sub-project; activity time
is a poor discriminator when that sub-project runs in an environment the log barely
tracks). This removes the largest class of false positives (sub-project side-commits
on a shared parent feature/branch).

### 3b. Then select clients
**Bill a (post-fold) client only if it has ≥ N commits OR ≥ T hours of activity**
that day (start with N≈3, T≈1.0 h and tune). Rank qualifying clients by combined
signal and take the top few.

- **Do not assume bill ∝ activity.** Sometimes a high-signal client is omitted
  entirely (judgement / fixed-price / not-yet-billable). Those days are out of scope.
- Residual misses are inherent: a client billed off a *single* commit, or < the
  activity threshold, can't be recovered without tanking precision. Accept the floor.

---

## 4. Titles — branch name first, then keywords

Titles are **persistent epic labels reused for days or weeks**, not per-day commit
summaries. Algorithm, in priority order:

1. **Branch name wins.** Extract every branch slug from each commit (bracketed
   `[hotfix/xyz]` *and* inline "merge … into xyz"). Drop `master`/`main`/`origin`/
   etc. Take the **most frequent** remaining slug for that client and map it to a
   title via your local vocabulary table. (Dominant branch, not first match.)
2. **Keyword fallback** on the message text when no feature branch is present.
3. **Per-client default** otherwise.

Prefer the label used on the **nearest prior day** for the same client + theme
(carry the epic forward) — this also covers the case where today's commits don't
mention the epic the work is billed under.

> Keep the actual slug→title vocabulary in `ENTRY_GUIDEBOOK.local.md`, not here.

**Implementation note:** if your git module stores the commit message + file list in
a single text field (prefixed with the branch), parse that field — the dedicated
`title` column may be empty.

---

## 5. Project field & repo→group mapping

- Map each repository to its group via config (§0b); several repos may map to one
  group, and one feature branch may span repos of *different* groups.
- **Shared-branch fold (precision rule):** before counting commits, collapse commits
  that share a feature branch across repos into the group that owns the branch — the
  other group's commits on that branch are part of the same feature, not a separate
  entry.
- Pick the `:Project` suffix by theme (feature dev vs incident vs ops) from the
  group's allowed projects.

---

## 6. Out-of-scope days (need human judgement)

Do not auto-fill, and exclude from scoring:

- **No-trace billed time** — meetings, review, planning, pairing that the log can't
  see; sometimes hours billed far exceed any signal.
- **Deliberate omission** — a client with strong signal you chose not to bill.
- **Leave / holidays** — a full-day fixed entry with no work signal.
- **Anomalous totals** — days you under- or over-billed relative to activity.

Detect these and surface them as low-confidence drafts or skips, never silent fills.

---

## 7. Confidence & review

Emit each entry with a confidence tag (high = commits + activity + known epic;
medium = one signal only / inferred title; low = single-commit client, extra client,
or out-of-scope day). Always present as a **draft to confirm**.

---

## 8. Validation approach

Implement the rules as a deterministic predictor and score it against your real past
entries: client-set F1, project-set F1, title accuracy, and hours MAE (using the
§2b model, not raw sums). Sweep thresholds (AFK gap, commit/activity cutoffs,
sub-project fold) to fit your own history. Re-run after any rule change.

Typical outcome on derivable days: **client/project selection becomes essentially
solved**; **billable-hours total lands within ~±1 h**; **titles are the soft spot**
(carry-forward epics, one-off ad-hoc titles, and signal that lives only in file
paths cap accuracy). Hours error concentrates in the daily *total* (offline/meeting
time the log never saw), not the split across clients.
