# /apply: a job-application prep pipeline for Claude Code

Type `/apply to devops roles in dubai` and Claude Code finds real openings, writes a CV tailored to each one from your own facts, has a blind AI recruiter score it, and saves a folder per job with the CV, the link and a cheat sheet for when they call.

**It never applies for you.** You read every CV and submit it yourself.

```
/apply ──► apply-hunt ──► apply-cv ⇄ apply-ats ──► save
           (Haiku)        (Sonnet)   (Opus)
           finds jobs     tailors    blind recruiter,
                          the CV     pass at 60/100
```

## What you get

```
~/job-hunt/applications/
├─ master_list.json                       every job it has seen, so nothing is prepped twice
└─ Acme_Cloud-Engineer_4471859101/
   ├─ Jane_Doe_CV.pdf                     tailored to this job
   ├─ job_link.txt
   └─ notes.txt                           who they are, what the job is, the full post
```

`notes.txt` is the file you open when a recruiter calls, so you know who they are and what you applied for, even after the posting is gone.

## How it works

1. **Preflight.** It reads the role and location from your command, shows a 3-line plan and waits for your go.
2. **Hunt** (`apply-hunt`, Haiku). It searches LinkedIn's public job pages while logged out. If it finds fewer than 3 matches, it widens to similar titles and then one seniority level up.
   - A small Python helper (`li.py`) filters out jobs you've already seen in code, plus senior titles if your target is junior, so they cost no tokens.
   - It skips roles that need more experience than you have, nationals-only roles, and single-product roles.
3. **Tailor** (`apply-cv`, Sonnet). It writes a CV from your `record.json` only, mirroring the job's wording where it's true. Every job runs in parallel.
4. **Gate** (`apply-ats`, Opus). A fresh recruiter agent sees only the PDF and the job post, and scores it out of 100.
   - **Below 60:** its feedback goes to a fresh writer for one more round.
   - **Below 45 on round 1:** it's the wrong job, so it gets skipped.
   - **FLAG:** when the remaining fixes need things you don't have, the writer says so.
5. **Save** (`save.py`). It writes the folder and records the job in `master_list.json`.

### Rules it won't break

- **It never submits an application.**
- **Nothing gets invented.** Every claim on a CV has to trace back to your `record.json`. Anything under `never_claim` or `confidential` stays off.
- **Logged out only.** No LinkedIn login, no stored passwords or cookies, and a 3–8 second pause between requests.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- **Windows with Microsoft Word.** CVs are exported to PDF through Word, which also measures how many lines are free on the page.
- Node.js 18+ and Python 3.10+

## Setup

Setup is the heavy part. Your CVs can only be as good as your `record.json`, so it's worth doing properly.

**1. Install**

```powershell
git clone https://github.com/hz-Solaire/claude-apply-skill.git
cd claude-apply-skill
powershell -ExecutionPolicy Bypass -File install.ps1
```

This copies two skills (`apply`, `apply-setup`) and three agents (`apply-hunt`, `apply-cv`, `apply-ats`) into `~/.claude`, installs the `docx` library, and creates your data folder at `~/job-hunt`. It overwrites any existing skill or agent with those names. To keep your data elsewhere, set `APPLY_HOME` before installing and before running Claude Code.

**2. Build your record: `/apply-setup`**

Open Claude Code and run `/apply-setup`. Have your **current CV** ready (PDF or DOCX).
- **It reads your CV** and drafts `record.json`: your roles broken into individual facts with their numbers, plus projects, education and skills.
- **It interviews you one question at a time** for everything a CV can't tell it: target roles and seniority, default location, languages, what your contact line shows, real numbers for vague bullets, things you never want claimed, client names to keep confidential, and your CV preferences.
- **It asks whether you want a page limit:** 1 page, 2 pages, or none.
- **It does a test build** of a general CV so you know Word export works.
- **Optionally, it calibrates the gate:** paste a job you know is a good fit and see how the recruiter scores you.

Run `/apply-setup` again any time your facts change: a new job, a cert, a project.

**3. Run it**

```
/apply to cloud engineer roles in lisbon
/apply to devops roles in saudi
```

Every job it saves is recorded as `applied` in `master_list.json`, so it never comes up again. Read each CV and send it yourself.

## Cost

These are rough figures from real runs:

| Step | Model | Tokens |
|---|---|---|
| Hunt pass | Haiku | ~55k |
| CV round | Sonnet | ~42k |
| Recruiter score | Opus (xhigh effort) | ~16k |

A 5-job run with one revision round is roughly 400–500k tokens. The recruiter stays on Opus on purpose. In testing, Sonnet ranked a stretch job above the best-fit one, and a gate that can't tell those apart is useless.

## Tuning

- **Threshold:** `THRESHOLD = 60` in `skills/apply/SKILL.md`.
  - This recruiter is harsher than keyword tools like Jobscan. A CV Jobscan rated 70% scored 48 here.
  - A clear shortlist scored 79, and a real-but-stretch job scored 60.
  - Use the calibration step in `/apply-setup` to check where your own CVs land.
- **Page limit:** `cv_preferences.max_pages` in `record.json` (1, 2, or `null`).
- **Section order:** `cv_preferences.section_order` in `record.json`.
- **What the hunt screens for:** `target.stack_keywords` in `record.json`.

## Disclaimer

- **LinkedIn's terms.** `li.py` reads LinkedIn's public, logged-out job pages slowly and in small volumes. LinkedIn's User Agreement restricts automated access to its site. Use this for your own job search, at your own risk, and stop if LinkedIn blocks you (the helper stops by itself on a sign-in wall or rate limit).
- **Your responsibility.** AI-written CVs can still be wrong. Read every CV before you send it. You're responsible for everything you submit.
- **Limits.** Windows and Word only for now. LinkedIn changes its page markup from time to time, which can break `li.py` until its patterns are updated.

## License

MIT
