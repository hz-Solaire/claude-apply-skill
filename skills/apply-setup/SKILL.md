---
name: apply-setup
description: One-time setup for /apply. Asks for your current CV, turns it into record.json (the only source of facts the CV writer may use), interviews you one question at a time for anything missing (including whether you want a page limit), then runs a test build so you know the pipeline works. Manual trigger only. Run it again any time your facts change.
disable-model-invocation: true
---

# /apply-setup: build your record.json

`record.json` is the heart of /apply. The CV writer may only use facts that are in it, so everything the user wants on a CV has to land here, accurately.

- `HOME_DIR` = the `APPLY_HOME` environment variable, or `~/job-hunt`
- `RECORD` = `HOME_DIR/record.json`
- `TEMPLATE` = `$HOME/.claude/skills/apply-setup/record.example.json`, which shows the full shape with a fake example person

**Interview rule:** ask **one question at a time**, and wait for the answer before asking the next.

## 1. Get their current CV (always first)

Ask: **"What's your current CV? Give me a file path (PDF or DOCX) or paste the text."**

Don't continue without it. If they have no CV at all, say you'll build the record by interview instead, and start with their most recent role.

Read the CV fully. If `RECORD` already has real content (it isn't the template), read that too, and treat this run as an update, not a rewrite.

## 2. Draft the record

Using `TEMPLATE`'s structure, fill in everything the CV supports:
- **`personal`**: the name and contact details as they appear on the CV
- **`education`**
- **`experience[]`**: one entry per role, broken into `facts`
  - one fact per achievement, keeping every number
  - a `keywords` list per fact
  - any client names go under `confidential`
- **`projects`, `volunteering`, `achievements`, `certifications`**
- **`skills`**: the hard skills grouped, plus soft skills

Keep the CV's exact wording for titles, company names and dates.

## 3. Interview for the gaps

Ask these one at a time. Skip any the CV already answers clearly.

1. **Target:** which roles and what seniority (e.g. "junior DevOps / Cloud, 0–2 years")? Which location should searches default to?
2. **Nationality:** used only to skip "nationals only" postings for other countries. They can decline to answer.
3. **Languages** and level for each.
4. **Page limit:** "Do you want your CV held to a page limit? 1 page, 2 pages, or no limit?" Store the answer in `cv_preferences.max_pages` (1, 2, or null).
5. **Contact line:** which of email, phone, LinkedIn, GitHub and location should appear? Store the exact strings, in order, in `personal.cv_contact`.
6. **Headline and titles:** the headline to use, and whether job titles must match HR records exactly.
7. **Numbers:** for each role with vague bullets, ask once for real numbers (users, services, time saved, incident duration). Only record what they confirm.
8. **Never claim:** anything they don't want on a CV, or skills they only half know. These go in `skills.never_claim`.
9. **Confidential names:** clients or partners that must never appear.
10. **Preferences:** section order, tone, words to avoid. These go in `cv_preferences`.

Never guess. Anything they don't know or skip stays `null`.

## 4. Save and confirm

Write `RECORD`, validate that it parses, and show a short summary: the number of roles, facts, projects and skills, the page limit, the contact line and the target. Ask if anything is wrong.

## 5. Test build

1. Write a general CV from the record to `HOME_DIR/general_cv.json`, in the same shape `apply-cv` uses.
2. Run:
   ```
   node "$HOME/.claude/skills/apply/build.js" "HOME_DIR/general_cv.json" "HOME_DIR/General_CV.pdf" <max_pages or omit>
   ```
3. If it fails because Word is missing, tell them. /apply needs Microsoft Word on Windows for PDF export.
4. If it's over the page limit, trim the general CV only (not the record) and rebuild.

Tell them where the PDF is and ask them to open it and check that it looks right.

## 6. Optional: calibrate the gate

Offer this once: "Want to see how the recruiter scores you? Paste a job post you know is a good fit." If they say yes:
1. Save the post to `HOME_DIR/calibration_jd.txt`.
2. Spawn **apply-ats** with `CV` = `HOME_DIR/General_CV.pdf` and `JD` = that file.
3. Report the score and verdict.

The default bar in /apply is 60, where 79 read as a clear shortlist and 60 as a stretch. If their good-fit job scores far below 60 on the general CV, suggest adjusting `THRESHOLD` in `$HOME/.claude/skills/apply/SKILL.md`.

Finish with: "You're set. Try `/apply to <role> roles in <city>`."
