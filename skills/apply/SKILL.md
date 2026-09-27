---
name: apply
description: Job-application prep pipeline. apply-hunt finds roles on LinkedIn's public job pages, apply-cv tailors a CV per job from your record.json, and a blind apply-ats recruiter gates it by score. Saves a folder per job plus a master list so nothing gets prepped twice. Never submits applications. Manual trigger only, e.g. "/apply to devops roles in dubai". Run /apply-setup first.
disable-model-invocation: true
---

# /apply: hunt, tailor, gate, save

You're the orchestrator. You don't hunt, write or grade CVs yourself: you drive the three agents and report honestly. **Never submit or apply to anything.** The candidate applies themselves, using the folders.

## Paths and parameters

- `HOME_DIR` = the `APPLY_HOME` environment variable, or `~/job-hunt` if it's unset
- `RECORD` = `HOME_DIR/record.json`. If it's missing or still the example, stop and tell them to run `/apply-setup`.
- `MASTER` = `HOME_DIR/applications/master_list.json`
- `SKILL_DIR` = `$HOME/.claude/skills/apply`
- `WORK` = `<your session scratchpad dir>/apply`
- `MAX_PAGES` = `cv_preferences.max_pages` from the record. It can be empty, meaning no page limit.
- `THRESHOLD` = 60, `MAX_ROUNDS` = 2, `MIN_JOBS` = 3, `MAX_JOBS` = 5
  - The threshold was calibrated with Opus as the recruiter:
    - a clear shortlist scored 79
    - a stretch job scored 60
    - a CV Jobscan rated 70% scored 48
  - The recruiter must stay on Opus. Sonnet ranked a stretch job above the best-fit one.

## Token discipline

- **Pass paths, never content.** Agents read files themselves.
- **Never resume an agent for a new round or a new hunt pass.** A resumed agent re-reads its whole history. Spawn fresh ones.
- **Relay only** the score, the verdict and the next action. Never paste agent reports back to the user.

## 0. Preflight: measure twice

1. **Parse the request.** `ROLE` defaults to `target.roles[0]` and `LOCATION` to `target.default_search_location`; a place named in the request overrides the location.
2. **Build `PROFILE`** in one line from the record: `target.seniority`, `target.roles`, `personal.nationality` and the core stack.
3. **Show the plan in 3 lines and wait for "go":** role, location, max jobs, page limit. Clear up anything ambiguous now, one question at a time.

## 1. Hunt

Spawn **apply-hunt** with `ROLE`, `LOCATION`, `PROFILE`, `MIN` = `MIN_JOBS`, `MAX` = `MAX_JOBS` and `OUT` = `WORK`. It returns a JSON array of jobs, each with a `dir` holding `jd.txt` and a `notes.txt` header. Every job it opened is already marked as seen.

If it returns zero jobs, relay its one-line reason and stop.

## 2. Tailor loop, all jobs in parallel

Parallel Word exports are fine, so spawn every job's round-1 apply-cv together. Score each job as its CV lands.

For each job, for `round` = 1..`MAX_ROUNDS`:
1. **Spawn a fresh apply-cv** with `JD` = `<dir>/jd.txt`, `RECORD`, `WORK` = `<dir>`, `ROUND` and `MAX_PAGES`. On round 2, add `FEEDBACK`: the recruiter's CONCERNS and TO RAISE lines only.
2. **`STATUS: FLAG`:** stop. The job is flagged with its `FLAG_REASON`.
3. **Spot-check `cv.json` before scoring:**
   - `contact` equals `personal.cv_contact`
   - every summary claim has a fact behind it in the record
   - no story is told twice
   - nothing from `never_claim` or `confidential` appears

   Fix mechanical misses yourself with a one-line JSON edit and a rebuild.
4. **Spawn a fresh apply-ats** with only `CV` = `<dir>/r<round>.pdf` and `JD` = `<dir>/jd.txt`.
5. **`SCORE` ≥ `THRESHOLD`:** passed. Stop.
6. **Round 1 under 45:** it's the wrong job, not a weak CV. Run `save.py --skip` and move on. If you're short of jobs, spawn a fresh apply-hunt for replacements.

If the job still hasn't passed after round 2, flag it: "gate not met (best NN)". The final CV is the highest-scoring round's PDF.

## 3. Save

```
python "SKILL_DIR/save.py" <dir> <final_pdf> <job_id> "<company>" "<title>" "<location>" "<url>" <best score or -> ["<flag reason>"]
```

- **What it does:** creates `HOME_DIR/applications/<Company>_<Title>_<JobID>/` with `<Name>_CV.pdf`, `job_link.txt` and `notes.txt` (with the full JD appended), and records the job as `applied`.
- **Dropping a job:** `save.py --skip <job_id> "<company>" "<title>" "<url>" "<reason>"`.
- **Status:** every saved job is recorded as `applied`, on the assumption that the user sends what gets prepped. Any entry counts as seen, so nothing comes up twice.

## 4. Report

One table: company | role | score / verdict | folder. Below it, one line per flag. Then stop.
