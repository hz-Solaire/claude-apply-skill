"""Save one prepped job into $APPLY_HOME/applications and record it in master_list.json.
  python save.py <job_dir> <final_pdf> <job_id> <company> <title> <location> <url> <score|-> [flag_reason]
  python save.py --skip <job_id> <company> <title> <url> <reason>     # seen, no folder
  python save.py --skip-file <rejects.json>   # [{"job_id","company","title","url","reason"}, ...]
job_dir must hold hunt's notes.txt (header only is fine) and jd.txt; the full JD is appended to notes.txt.
Re-saving the same job_id replaces its folder contents and master entry.
"""
import datetime, json, os, re, shutil, sys

HOME = os.environ.get('APPLY_HOME') or os.path.join(os.path.expanduser('~'), 'job-hunt')
APPS = os.path.join(HOME, 'applications')
try:  # the CV file is named after the candidate, e.g. Jane_Doe_CV.pdf
    NAME = json.load(open(os.path.join(HOME, 'record.json'), encoding='utf-8'))['personal']['name']
except (OSError, ValueError, KeyError):
    NAME = 'My'
CV_FILE = re.sub(r'\s+', '_', NAME.strip()) + '_CV.pdf'


def slug(s):
    s = re.sub(r'[^A-Za-z0-9]+', '-', s.encode('ascii', 'ignore').decode()).strip('-')
    return s or 'x'


def record(*new):
    master = os.path.join(APPS, 'master_list.json')
    entries = json.load(open(master, encoding='utf-8')) if os.path.exists(master) else []
    ids = {e['job_id'] for e in new}
    entries = [e for e in entries if e['job_id'] not in ids] + list(new)
    os.makedirs(APPS, exist_ok=True)
    with open(master, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


today = datetime.date.today().isoformat()
skip = lambda job_id, company, title, url, reason: {'job_id': job_id, 'company': company, 'title': title, 'url': url,
                                                    'folder': None, 'prepared': today, 'status': 'skipped', 'skip_reason': reason}
if sys.argv[1] == '--skip':
    record(skip(*sys.argv[2:7]))
    sys.exit(print(f'skipped {sys.argv[2]}'))
if sys.argv[1] == '--skip-file':
    rejects = json.load(open(sys.argv[2], encoding='utf-8'))
    record(*(skip(r['job_id'], r['company'], r['title'], r['url'], r['reason']) for r in rejects))
    sys.exit(print(f'skipped {len(rejects)}'))

job_dir, pdf, job_id, company, title, location, url, score, *flag = sys.argv[1:]
folder = os.path.join(APPS, f'{slug(company)[:30]}_{slug(title)[:40]}_{job_id}')
os.makedirs(folder, exist_ok=True)
shutil.copyfile(pdf, os.path.join(folder, CV_FILE))
SEP = '------------------------- FULL JOB DESCRIPTION -------------------------'
notes = open(os.path.join(job_dir, 'notes.txt'), encoding='utf-8').read()
if SEP not in notes:
    notes = notes.rstrip() + f'\n\n{SEP}\n' + open(os.path.join(job_dir, 'jd.txt'), encoding='utf-8').read()
with open(os.path.join(folder, 'notes.txt'), 'w', encoding='utf-8') as f:
    f.write(notes)
with open(os.path.join(folder, 'job_link.txt'), 'w', encoding='utf-8') as f:
    f.write(url + '\n')
record({'job_id': job_id, 'company': company, 'title': title, 'location': location, 'url': url,
        'folder': os.path.basename(folder), 'prepared': today,
        'score': None if score == '-' else int(score), 'flagged': bool(flag),
        'flag_reason': flag[0] if flag else None, 'status': 'applied', 'applied': today})
print(folder)
