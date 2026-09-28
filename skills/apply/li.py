"""LinkedIn public (logged-out) job pages -> compact JSON on stdout. Stdlib only, never logs in.
  python li.py search "<keywords>" "<location>" <f_E: 2 | 2,3> [start] [days=30]
      drops job IDs already in $APPLY_HOME/applications/master_list.json, and senior/lead/manager titles when target.seniority is junior/entry
  python li.py job <job_id> <out_dir>
      writes <out_dir>/<job_id>/jd.txt; prints a screening summary, not the description
  python li.py company <linkedin company url>
Every call waits 3-8s first so a run stays gentle. Blocked/rate-limited -> {"error": ...}, exit 2.
"""
import html, json, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'
HOME = os.environ.get('APPLY_HOME') or os.path.join(os.path.expanduser('~'), 'job-hunt')
MASTER = os.path.join(HOME, 'applications', 'master_list.json')
SENIOR = re.compile(r'\b(senior|sr|lead|principal|staff|head|manager|director|architect|chief|vp)\b', re.I)
STACK = ['GCP', 'Google Cloud', 'AWS', 'Azure', 'Terraform', 'Ansible', 'Kubernetes', 'Docker', 'Jenkins', 'ArgoCD',
         'GitLab', 'GitHub Actions', 'Prometheus', 'Grafana', 'OpenTelemetry', 'Vault', 'Linux', 'Python', 'Bash',
         'PowerShell', 'Splunk', 'SAP', 'ServiceNow', 'Windows Server', 'Active Directory', 'VMware']
try:  # record.json tunes the screening: which stack keywords to look for, and the candidate's seniority
    TARGET = json.load(open(os.path.join(HOME, 'record.json'), encoding='utf-8')).get('target', {})
except (OSError, ValueError):
    TARGET = {}
STACK = TARGET.get('stack_keywords') or STACK
JUNIOR = re.search(r'junior|entry|graduate|intern|fresh', TARGET.get('seniority') or '', re.I)


def get(url):
    time.sleep(random.uniform(3, 8))
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if 'authwall' in r.geturl() or '/login' in r.geturl():
                raise SystemExit(fail(f'sign-in wall at {r.geturl()}'))
            return r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:  # LinkedIn answers 429 or 999 when it's throttling
        raise SystemExit(fail(f'HTTP {e.code} for {url}'))


def fail(msg):
    print(json.dumps({'error': msg}))
    return 2


def text(s):
    s = re.sub(r'<br\s*/?>|</p>|</li>|</h\d>', '\n', s)
    s = re.sub(r'<li[^>]*>', '- ', s)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    return re.sub(r'\n\s*\n+', '\n\n', re.sub(r'[ \t]+', ' ', s)).strip()


def grab(pat, s):
    m = re.search(pat, s, re.S)
    return text(m.group(1)) if m else None


def search(kw, loc, levels, start='0', days='30'):
    q = urllib.parse.urlencode({'keywords': kw, 'location': loc, 'f_E': levels, 'f_TPR': f'r{int(days) * 86400}', 'start': start})
    s = get('https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?' + q)
    seen = {e['job_id'] for e in json.load(open(MASTER, encoding='utf-8'))} if os.path.exists(MASTER) else set()
    jobs, dropped = [], 0
    for li in s.split('<li')[1:]:
        jid = re.search(r'jobPosting:(\d+)', li)
        if not jid:
            continue
        title = grab(r'base-search-card__title">(.*?)</h3>', li) or ''
        if jid.group(1) in seen or (JUNIOR and SENIOR.search(title)):
            dropped += 1
            continue
        jobs.append({'job_id': jid.group(1), 'title': title,
                     'company': grab(r'base-search-card__subtitle">(.*?)</h4>', li),
                     'location': grab(r'job-search-card__location">(.*?)</span>', li),
                     'posted': grab(r'<time[^>]*>(.*?)</time>', li)})
    return {'dropped_seen_or_senior': dropped, 'jobs': jobs}


def mark_screened(jid, company_, title):
    # every fetched job counts as seen, so rejects never cost tokens again; save.py upgrades keepers to "applied"
    entries = json.load(open(MASTER, encoding='utf-8')) if os.path.exists(MASTER) else []
    if any(e['job_id'] == jid for e in entries):
        return
    entries.append({'job_id': jid, 'company': company_, 'title': title, 'url': f'https://www.linkedin.com/jobs/view/{jid}',
                    'folder': None, 'prepared': time.strftime('%Y-%m-%d'), 'status': 'screened'})
    os.makedirs(os.path.dirname(MASTER), exist_ok=True)
    with open(MASTER, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)


def snippets(pat, s, n=4):
    return list(dict.fromkeys(m.strip() for m in re.findall(rf'[^.\n]{{0,40}}{pat}[^.\n]{{0,30}}', s, re.I)))[:n]


def job(jid, out_dir):
    s = get(f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}')
    slug = re.search(r'linkedin\.com/company/([\w-]+)', s)
    title, company_ = grab(r'topcard__title">(.*?)</h2>', s), grab(r'topcard__org-name-link[^>]*>(.*?)</a>', s)
    desc = grab(r'show-more-less-html__markup[^>]*>(.*?)</div>', s) or ''
    os.makedirs(os.path.join(out_dir, jid), exist_ok=True)
    with open(os.path.join(out_dir, jid, 'jd.txt'), 'w', encoding='utf-8') as f:
        f.write(f'{title} - {company_}\n\n{desc}\n')
    mark_screened(jid, company_, title)
    return {'job_id': jid, 'url': f'https://www.linkedin.com/jobs/view/{jid}', 'title': title, 'company': company_,
            'company_url': slug and f'https://www.linkedin.com/company/{slug.group(1)}',
            'location': grab(r'<span class="topcard__flavor topcard__flavor--bullet">(.*?)</span>', s),
            'posted': grab(r'posted-time-ago__text[^>]*>(.*?)</span>', s),
            'criteria': dict(zip((text(h) for h in re.findall(r'job-criteria-subheader">(.*?)</h3>', s, re.S)),
                                 (text(t) for t in re.findall(r'job-criteria-text[^>]*>(.*?)</span>', s, re.S)))),
            'years': snippets(r'\d+\s*(?:\+|-|–|to)?\s*\d*\s*\+?\s*years?', desc),
            'nationality': snippets(r'(?:nationals?\b|nationality|citizens? only|saudization)', desc),
            'visa_iqama': snippets(r'(?:iqama|transferable|visa)', desc, 2),
            'certs': snippets(r'certif\w*', desc, 3),
            'stack': [k for k in STACK if re.search(rf'\b{re.escape(k)}\b', desc, re.I)],
            'jd_file': os.path.join(out_dir, jid, 'jd.txt'), 'jd_chars': len(desc)}


def company(url):
    s = get(url)
    dd = lambda k: grab(rf'<dt[^>]*>\s*{k}\s*</dt>\s*<dd[^>]*>(.*?)</dd>', s)
    return {'name': grab(r'<h1[^>]*>(.*?)</h1>', s),
            'about': (grab(r'about-us__description"[^>]*>(.*?)</p>', s) or '')[:500],
            'website': (dd('Website') or '').split('External link')[0].strip() or None,
            'industry': dd('Industry'), 'size': dd('Company size'), 'hq': dd('Headquarters')}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, *args = sys.argv[1:]
    print(json.dumps({'search': search, 'job': job, 'company': company}[cmd](*args), ensure_ascii=False))
