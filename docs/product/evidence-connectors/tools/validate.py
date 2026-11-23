import os
"""Validate every check key, control code, objective code, artifact key and template key referenced by the
reconciliation outputs. Each must exist in seed content, in checks-proposed.json, or in the controls.json proposals.
Run: PYTHONUTF8=1 python validate.py  (exit code 1 on any problem)"""
import json, re, csv, sys, glob, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')).replace(os.sep, '/')
DOCS = ROOT + '/docs/product/evidence-connectors/'
C = ROOT + '/backend/src/verity/seed/content/'
J = lambda p: json.load(open(p, encoding='utf-8'))
FAM = r'(?:BC|CS|DM|EP|GOV|HR|IAM|LM|NS|PE|SD)'

checks = {c['key'] for c in J(C + 'automation/checks.json')}
caps = J(C + 'automation/capabilities.json')
capk = {c['key'] for c in caps}
provk = {p['key'] for c in caps for p in c['providers']}
arts = {a['key'] for a in J(C + 'objectives/artifacts.json')}
objs = {o['code'] for x in J(C + 'objectives/objectives.json') for o in x['objectives']}
ctrls = {t['code'] for fw in ('soc2', 'iso27001') for t in J(C + fw + '/control_templates.json')}
tmpls = {t['key'] for t in J(C + 'policies/document_templates.json')}

P = J(DOCS + 'checks-proposed.json')
pchecks = {c['key'] for c in P['checks']}
aliases = set(P['alias_index'])
parts_ = {a['key'] for a in P['artifacts_proposed']} | {x for a in P['artifacts_proposed'] for x in a.get('aliases', [])}
pctrls, pobjs = set(), set()
for f in glob.glob(DOCS + 'coverage/*.controls.json'):
    for e in J(f):
        if e['decision'] == 'add':
            pctrls.add(e['control'])
        for s in e.get('successors') or []:
            pctrls.add(s['code'])
        for o in e['objective_changes']:
            pobjs.add(o['code'])
            if o.get('to'):
                pobjs.add(o['to'])
            for m in o.get('methods') or []:
                parts_.update(m.get('artifacts') or [])
        parts_.update(a if isinstance(a, str) else a.get('key') for a in e.get('new_artifacts') or [])
for f in glob.glob(DOCS + 'coverage/*.json'):
    if f.endswith('.controls.json') or 'needs-resolution' in f:
        continue
    for e in J(f):
        if e.get('artifact_status') == 'proposed':
            parts_.add(e['artifact'])
pcaps = {'business_applications', 'ai_providers', 'verity_identity', 'verity_members', 'learning_platform', 'esignature',
         'background_screening', 'public_web', 'productivity_suite', 'verity_notifications'}
pprov = {'defender_endpoint', 'hibob', 'roster_import', 'verity_agent', 'jamf_protect', 'hubspot', 'intercom', 'zendesk', 'posthog',
         'sendgrid', 'resend', 'openai', 'anthropic', 'docusign', 'checkr', 'certn'}

ALLC, ALLK, ALLA, ALLO = ctrls | pctrls, checks | pchecks, arts | parts_, objs | pobjs
errs = []
def chk(kind, val, ok, where):
    if val and val not in ok:
        errs.append(f'{where}: unknown {kind} {val}')

for c in P['checks']:
    w = 'checks-proposed ' + c['key']
    assert c['key'] not in checks, c['key']
    for m in c['controls']:
        chk('control', m['code'], ALLC, w)
        assert m['coverage'] in ('full', 'partial'), w
    for a in c['artifacts']:
        chk('artifact', a, ALLA, w)
    for r in c['related']:
        chk('check', r['key'], ALLK, w)
    for a in c['aliases']:
        chk('alias', a, aliases, w)
    for cp in c['capabilities'] + c.get('requires', []):
        chk('capability', cp, capk | pcaps, w)
    for p, lv in c['providers'].items():
        chk('provider', p, provk | pprov, w)
        assert lv in ('supported', 'partial', 'not_possible'), w
    assert set(c['implementations']) == {p for p, l in c['providers'].items() if l != 'not_possible'}, w
    assert c['status'] == 'proposed'
for e in P['existing_check_extensions']:
    w = 'extension ' + e['key']
    chk('check', e['key'], checks, w)
    for m in e.get('add_controls', []):
        chk('control', m['code'], ALLC, w)
    for a in e.get('add_artifacts', []):
        chk('artifact', a, ALLA, w)
    for ch in e.get('changes', []):
        chk('control', ch.get('control'), ALLC, w)
        chk('control', ch.get('to_control'), ALLC, w)
    for p in e.get('add_implementations', {}):
        chk('provider', p, provk | pprov, w)
    for cp in e.get('add_capabilities', []):
        chk('capability', cp, capk | pcaps, w)
for p, v in P['provider_additions'].items():
    chk('provider', p, provk | pprov, 'provider_additions')
    for k in list(v['existing']) + list(v['proposed']):
        chk('check', k, ALLK, 'provider_additions ' + p)
for a, k in P['alias_index'].items():
    assert a not in checks and a not in pchecks, a
    chk('check', k, ALLK, 'alias_index')

N = J(DOCS + 'coverage/needs-resolution.json')
for r in N['needs']:
    w = 'needs ' + r['artifact']
    chk('artifact', r['artifact'], ALLA, w)
    chk('control', r['control'], ALLC, w)
    for o in r['objectives']:
        chk('objective', o, ALLO, w)
    for k in [r.get('check')] + r.get('also', []):
        chk('check', k, ALLK, w)
    assert (r['match'] == 'unresolved') == ('check' not in r), w
assert len(N['needs']) == N['counts']['entries']

for row in csv.DictReader(open(DOCS + '07-control-matrix.csv', encoding='utf-8')):
    w = 'matrix ' + row['code']
    chk('control', row['code'], ALLC, w)
    for col in ('connector_checks_existing', 'connector_checks_proposed', 'verity_checks_existing', 'verity_checks_proposed'):
        for k in row[col].split():
            chk('check', k, ALLK, w)
    for t in row['document_templates'].split():
        chk('template', t, tmpls, w)

ck_re = re.compile(r'^(?:idp|vault|people|hr|devices|endpoint|cloud|assets|vcs|ci|tickets|alerts|observability|edge|scanner|apps|ai|verity)\.[a-z0-9_.]+$')
for name in ('05-check-registry.md', '06-control-changes.md', '07-control-matrix.md', '08-owner-decisions-raw.md'):
    t = open(DOCS + name, encoding='utf-8').read()
    for tok in re.findall(r'`([^`\s]+)`', t):
        if tok in P['observation_types_added']:
            continue  # observation type names, not checks
        if ck_re.match(tok):
            chk('check', tok, ALLK | aliases, name)
        elif re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)+', tok):
            chk('artifact or template', tok, ALLA | tmpls, name)
    for code in set(re.findall(rf'(?<![A-Za-z-]){FAM}-\d{{2}}(?![\d])', t)):
        chk('control', code, ALLC, name)
    for o in set(re.findall(rf'(?<![A-Za-z-])({FAM}-\d{{2}}\.[A-Z])(?![A-Za-z])', t)):
        chk('objective', o, ALLO, name)
for name in ('05-check-registry.md', '06-control-changes.md', '07-control-matrix.md', '07-control-matrix.csv',
             '08-owner-decisions-raw.md', 'checks-proposed.json', 'coverage/needs-resolution.json'):
    t = open(DOCS + name, encoding='utf-8').read()
    if '\u2014' in t or '\u2013' in t:
        errs.append(f'{name}: contains an em or en dash')

for e in sorted(set(errs)):
    print(e)
print(f'{len(set(errs))} problems; checked {len(P["checks"])} proposed checks, {len(P["existing_check_extensions"])} extensions, {len(N["needs"])} needs')
sys.exit(1 if errs else 0)
