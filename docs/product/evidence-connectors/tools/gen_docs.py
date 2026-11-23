import os
"""Generate 05, 06, 07 (md + csv) and 08 from content, checks-proposed.json, needs-resolution.json and the parts.
Run after merge.py: PYTHONUTF8=1 python gen_docs.py"""
import json, collections, csv, io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')).replace(os.sep, '/')
DOCS = ROOT + '/docs/product/evidence-connectors/'
C = ROOT + '/backend/src/verity/seed/content/'
J = lambda p: json.load(open(p, encoding='utf-8'))

existing = {c['key']: c for c in J(C + 'automation/checks.json')}
caps = J(C + 'automation/capabilities.json')
capmap = {c['key']: c for c in caps}
artifacts = {a['key']: a for a in J(C + 'objectives/artifacts.json')}
objectives = J(C + 'objectives/objectives.json')
obj_count = {o['control']: len(o['objectives']) for o in objectives}
templates = {}
for fw in ('soc2', 'iso27001'):
    for t in J(C + fw + '/control_templates.json'):
        templates[t['code']] = t
treq = collections.defaultdict(list)
for fw in ('soc2', 'iso27001'):
    for r in J(C + fw + '/template_requirements.json'):
        treq[r['template_code']].append(r)
P = J(DOCS + 'checks-proposed.json')
N = J(DOCS + 'coverage/needs-resolution.json')
MG = J(HERE + '/merged.json')
proposed = {c['key']: c for c in P['checks']}
extmap = {e['key']: e for e in P['existing_check_extensions']}
ALIAS = P['alias_index']
canon = lambda k: ALIAS.get(k, k)
CF = ['gov-cs-hr', 'iam-ep-pe-ns-dm', 'sd-lm-bc']
ctl = {f: J(DOCS + 'coverage/' + f + '.controls.json') for f in CF}
cov = {f: J(DOCS + 'coverage/' + f + '.json') for f in CF}

def w(name, text):
    assert '\u2014' not in text and '\u2013' not in text, name
    open(DOCS + name, 'w', encoding='utf-8', newline='\n').write(text)

def esc(s):
    return str(s or '').replace('|', '/').replace('\n', ' ').strip()

def avail_by_p2(key):
    """A check source counts by end of Phase 2 when it is verity.* or one of its providers is available or Phase 2."""
    key = canon(key)
    if key.startswith('verity.'):
        return True
    provs = set()
    if key in existing:
        provs |= set(existing[key]['implementations'])
        provs |= set(extmap.get(key, {}).get('add_implementations', {}))
        capl = existing[key]['capabilities'] + extmap.get(key, {}).get('add_capabilities', [])
    elif key in proposed:
        provs |= set(proposed[key]['implementations'])
        capl = proposed[key]['capabilities']
    else:
        return False
    for cp in capl:
        for p in capmap.get(cp, {}).get('providers', []):
            if p['key'] in provs and (p['status'] == 'available' or p['phase'] == 'Phase 2'):
                return True
    return False

# ---------------------------------------------------------------------------------------------- successors
succ = {}  # code -> dict(name, origin, requirements, decision, tenant_impact, file)
for f, lst in ctl.items():
    for e in lst:
        if e['decision'] == 'add':
            s = (e.get('successors') or [{}])[0] if e.get('successors') else {}
            succ[e['control']] = {'name': e.get('name') or s.get('name'), 'origin': None, 'decision': 'add',
                                  'requirements': e.get('requirements') or s.get('requirements') or [], 'tenant_impact': e.get('tenant_impact'), 'file': f,
                                  'owner': s.get('owner_function'), 'applies_when': s.get('applies_when')}
        for s in e.get('successors') or []:
            if s['code'] == e['control']:
                continue
            succ[s['code']] = {'name': s['name'], 'origin': e['control'], 'decision': 'split', 'requirements': s.get('requirements', []),
                               'tenant_impact': e.get('tenant_impact'), 'file': f, 'takes': s.get('takes_objectives') or [],
                               'new': s.get('new_objectives') or [], 'owner': s.get('owner_function'), 'applies_when': s.get('applies_when')}

all_obj_changes = []
for f, lst in ctl.items():
    for e in lst:
        for o in e['objective_changes']:
            all_obj_changes.append(dict(o, _control=e['control'], _file=f))

def objectives_after(code):
    n = obj_count.get(code, 0)
    for o in all_obj_changes:
        oc = o['code'].rsplit('.', 1)[0]
        if o['change'] == 'add' and oc == code:
            n += 1
        if o['change'] == 'remove' and oc == code:
            n -= 1
        if o['change'] == 'move' and o.get('to'):
            if oc == code:
                n -= 1
            if o['to'].rsplit('.', 1)[0] == code:
                n += 1
    return n

# ================================================================================================ 07 matrix
rows = []
codes = sorted(set(templates) | set(succ), key=lambda c: (c.split('-')[0], int(c.split('-')[1])))
need_by_art = collections.defaultdict(list)
for r in N['needs']:
    need_by_art[(r['file'], r['artifact'], r['control'])].append(r)
for code in codes:
    shipped = code in templates
    reqs = treq.get(code, []) if shipped else succ[code]['requirements']
    rk = lambda r: r.get('requirement_key') or r.get('key')
    soc = sorted({rk(r).split(':', 1)[1] for r in reqs if rk(r).startswith('SOC2')})
    iso = sorted({rk(r).split(':', 1)[1] for r in reqs if rk(r).startswith('ISO27001')})
    arts = [(f, e) for f in CF for e in cov[f] if e['control'] == code]
    ph = collections.Counter(e['phase'] for f, e in arts)
    conn_e, conn_p, ver_e, ver_p, tmpl = set(), set(), set(), set(), set()
    auto = full = 0
    for f, e in arts:
        keys, fullkeys = set(), set()
        for p in e['planned']:
            if p.get('check'):
                keys.add(canon(p['check']))
                if p.get('fills') == 'full':
                    fullkeys.add(canon(p['check']))
            if p['kind'] == 'document' and p.get('template'):
                tmpl.add(p['template'])
        for r in need_by_art[(f'coverage/{f}.json', e['artifact'], code)]:
            if r.get('check'):
                keys.add(r['check'])
                if r['match'] == 'exact' and r.get('fills') == 'full':
                    fullkeys.add(r['check'])
        for k in keys:
            isnew = k in proposed
            if k.startswith('verity.'):
                (ver_p if isnew else ver_e).add(k)
            else:
                (conn_p if isnew else conn_e).add(k)
        if any(avail_by_p2(k) for k in keys):
            auto += 1
        if any(avail_by_p2(k) for k in fullkeys):
            full += 1
    n = len(arts)
    rows.append({
        'code': code, 'status': 'shipped' if shipped else 'proposed', 'family': code.split('-')[0],
        'name': templates[code]['name'] if shipped else succ[code]['name'],
        'origin': '' if shipped else (succ[code]['origin'] or 'new'),
        'soc2': ' '.join(soc), 'iso27001': ' '.join(iso),
        'objectives_shipped': obj_count.get(code, 0), 'objectives_proposed': objectives_after(code),
        'artifacts': n, 'P1': ph['P1'], 'P2': ph['P2'], 'P3': ph['P3'], 'people_only': ph['people-only'],
        'connector_checks_existing': ' '.join(sorted(conn_e)), 'connector_checks_proposed': ' '.join(sorted(conn_p)),
        'verity_checks_existing': ' '.join(sorted(ver_e)), 'verity_checks_proposed': ' '.join(sorted(ver_p)),
        'document_templates': ' '.join(sorted(tmpl)),
        'automated_by_p2': auto, 'automated_share_by_p2': f'{(auto / n * 100):.0f}%' if n else '',
        'full_automated_by_p2': full, 'full_automated_share_by_p2': f'{(full / n * 100):.0f}%' if n else '',
    })
buf = io.StringIO()
cw = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator='\n')
cw.writeheader()
cw.writerows(rows)
w('07-control-matrix.csv', buf.getvalue())

fam = collections.OrderedDict()
for r in rows:
    f = fam.setdefault(r['family'], collections.Counter())
    f['controls'] += 1
    f['proposed'] += r['status'] == 'proposed'
    for k in ('artifacts', 'P1', 'P2', 'P3', 'people_only', 'automated_by_p2', 'full_automated_by_p2'):
        f[k] += r[k]
tot = collections.Counter()
for f in fam.values():
    tot.update(f)
L = []
L += ['# 7. Control matrix', '',
      'One row per control: the 133 shipped controls and the 15 proposed ones (11 successors of splits, 4 additions).',
      'Generated from `coverage/*.json`, `coverage/*.controls.json`, `coverage/needs-resolution.json`,',
      '`checks-proposed.json` and the seed content. The full lists of check keys and templates per control are in',
      '[07-control-matrix.csv](07-control-matrix.csv); this page shows the counts.', '',
      '## How the columns are counted', '',
      '| Column | Meaning |', '|---|---|',
      '| Frameworks | SOC 2 criteria and ISO 27001 references mapped in `template_requirements.json` (shipped controls), or in the `*.controls.json` proposal (proposed controls). Mapping changes proposed for shipped controls are in [06-control-changes.md](06-control-changes.md), not here |',
      '| Objectives | Shipped count, then the count after the proposed adds, moves and removals |',
      '| P1, P2, P3, people | Artifact rows of the control in the coverage files, by the phase the researcher gave the artifact. "people" is people-only |',
      '| Conn, Verity | Distinct connector checks and Verity module checks named on the control\'s artifacts, including needs resolved in `needs-resolution.json`. Proposed keys are counted after aliases are resolved. "e+p" is existing plus proposed |',
      '| Docs | Distinct document templates named as sources |',
      '| Auto by P2 | Share of the control\'s artifacts with at least one check source (full or partial) that can run by the end of Phase 2: a `verity.*` check, or a connector check with a provider that is available or planned for Phase 2 in `capabilities.json`. Device, endpoint and HR checks do not count, because those providers are not planned |',
      '| Full by P2 | The same, counting only checks that fill the artifact in full (an exact need match, or a planned source marked `fills: full`). Under the pending automation rule only these can satisfy an artifact without a person (rule B); a partial check only takes satisfaction away (rule A, 01-evidence-model.md 1.2) |',
      '', '## By family', '',
      '| Family | Controls | Proposed | Artifacts | P1 | P2 | P3 | People only | Auto by P2 | Full by P2 |', '|---|---|---|---|---|---|---|---|---|---|']
for k, f in fam.items():
    L.append(f"| {k} | {f['controls']} | {f['proposed']} | {f['artifacts']} | {f['P1']} | {f['P2']} | {f['P3']} | {f['people_only']} | {f['automated_by_p2'] / f['artifacts'] * 100:.0f}% | {f['full_automated_by_p2'] / f['artifacts'] * 100:.0f}% |")
L.append(f"| All | {tot['controls']} | {tot['proposed']} | {tot['artifacts']} | {tot['P1']} | {tot['P2']} | {tot['P3']} | {tot['people_only']} | {tot['automated_by_p2'] / tot['artifacts'] * 100:.0f}% | {tot['full_automated_by_p2'] / tot['artifacts'] * 100:.0f}% |")
L += ['', 'Artifact rows count an artifact once per control it serves, so the total is higher than the 338 artifact types.', '',
      '## Per control', '',
      '| Code | Name | Status | SOC 2 | ISO 27001 | Objectives | P1 | P2 | P3 | People | Conn e+p | Verity e+p | Docs | Auto by P2 | Full by P2 |',
      '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
cnt = lambda s: len(s.split()) if s else 0
for r in rows:
    st = 'shipped' if r['status'] == 'shipped' else f"proposed ({'from ' + r['origin'] if r['origin'] != 'new' else 'new'})"
    ob = str(r['objectives_proposed']) if r['status'] == 'proposed' or r['objectives_shipped'] == r['objectives_proposed'] else f"{r['objectives_shipped']} to {r['objectives_proposed']}"
    L.append(f"| {r['code']} | {esc(r['name'])} | {st} | {esc(r['soc2'])} | {esc(r['iso27001'])} | {ob} | {r['P1']} | {r['P2']} | {r['P3']} | {r['people_only']} | "
             f"{cnt(r['connector_checks_existing'])}+{cnt(r['connector_checks_proposed'])} | {cnt(r['verity_checks_existing'])}+{cnt(r['verity_checks_proposed'])} | {cnt(r['document_templates'])} | {r['automated_share_by_p2'] or 'n/a'} | {r['full_automated_share_by_p2'] or 'n/a'} |")
noart = [r['code'] for r in rows if r['artifacts'] == 0]
L += ['', f"Controls with no artifact row in the coverage files: {', '.join(noart) if noart else 'none'}.", '']
w('07-control-matrix.md', '\n'.join(L))

# ================================================================================================ 05 registry
cap_order = [c['key'] for c in caps] + ['business_applications', 'ai_providers', 'learning_platform', 'verity_identity', 'verity_members']
prim = lambda caps_: caps_[0]
existing_by_cap = collections.defaultdict(list)
for k, c in existing.items():
    existing_by_cap[c['capabilities'][0]].append(k)
proposed_by_cap = collections.defaultdict(list)
for k, c in proposed.items():
    proposed_by_cap[prim(c['capabilities'])].append(k)
unres_by_cap = collections.defaultdict(collections.Counter)
unres_why = {}
for r in N['needs']:
    if r['match'] == 'unresolved':
        unres_by_cap[r['capability']][r['predicate']] += 1
        unres_why[r['predicate']] = (r['reason'], r['why'])
running_prov = {p['key'] for c in caps for p in c['providers'] if p['status'] == 'available'}
cnts = N['counts']
dg = MG['downgrades']
dg_check = [g for g in dg if g.get('check') and g.get('to') == 'partial']
dg_req = [g for g in dg if not g.get('check') and g.get('to') == 'partial']
dg_move = [g for g in dg if not g.get('check') and g.get('to') != 'partial']
lvl = {'supported': 'S', 'partial': 'P', 'not_possible': 'N'}

def provs(c):
    return ', '.join(f"{p} {lvl[l]}" for p, l in c['providers'].items()) or 'none'

def ctls(c):
    return ', '.join(f"{m['code']} {m['coverage'][0]}" for m in c['controls'])

L = ['# 5. Check registry', '',
     'The readable registry of every check: the 93 shipped in `seed/content/automation/checks.json` and the new ones',
     'the research proposes in [checks-proposed.json](checks-proposed.json). Grouped by capability. Proposals only:',
     'nothing here changes seed content (AUTHORING rule 8). Researched and reconciled 2026-11-23.', '',
     '## 5.1 Counts', '',
     '| Item | Count |', '|---|---|',
     f"| Shipped checks | {len(existing)} ({sum(1 for c in existing.values() if set(c['implementations']) & running_prov)} running: GitHub and Verity) |",
     f"| New check keys written by the researchers | {P['counts']['raw_keys_before_dedup']} |",
     f"| Aliases merged into another key | {P['counts']['aliases_merged']} |",
     f"| Proposed checks after deduplication | {P['counts']['proposed_checks']} |",
     f"| Shipped checks the research extends (providers, controls, capabilities or corrections) | {P['counts']['existing_checks_extended']} |",
     f"| Providers named | {P['counts']['providers_listed']} |",
     f"| NEED entries in the coverage files | {cnts['entries']} ({cnts['unique_predicates']} distinct predicates) |",
     f"| Needs resolved exactly / partly / unresolved | {cnts['by_match'].get('exact', 0)} / {cnts['by_match'].get('partial', 0)} / {cnts['by_match'].get('unresolved', 0)} |",
     f"| Coverage downgrades, check to control (full to partial) | {len(dg_check)} |",
     f"| Coverage downgrades, requirement to control (full to partial) | {len(dg_req)} |",
     '',
     '## 5.2 How to read this page', '',
     '- **Running**: the check has an implementation whose provider is available today (GitHub, Verity). **Planned**: in',
     '  `checks.json`, no running implementation. **Proposed**: new, in `checks-proposed.json`.',
     '- Providers: `S` supported, `P` partial (the connector document says why), `N` not possible.',
     '- Controls: code then `f` full or `p` partial.',
     '- **capability_match each** (proposed): a check written for several capabilities evaluates every connected provider',
     '  of those capabilities on its own and passes only when all pass. Today a check with several capabilities needs all of',
     '  them connected (for example `people.leavers_deprovisioned` needs an HR source and an identity provider). The',
     '  merges in 5.4 need this new rule so that one connected system cannot stand in for another (an identity provider',
     '  list must not pass for the code host list). It is an engine change for the outcome engine and the check runner.', '']
L += ['## 5.3 By capability', '']
for cp in cap_order:
    ex = sorted(existing_by_cap.get(cp, []))
    pr = sorted(proposed_by_cap.get(cp, []))
    un = unres_by_cap.get(cp, {})
    if not (ex or pr or un):
        continue
    name = capmap[cp]['name'] if cp in capmap else cp.replace('_', ' ').capitalize() + ' (proposed capability)'
    L += [f'### {name} (`{cp}`)', '']
    if cp in capmap:
        L += ['Catalogue: ' + ', '.join(f"{p['key']} ({p['status'] if p['status'] != 'planned' else p['phase']})" for p in capmap[cp]['providers']) + '.', '']
    if ex:
        L += ['Shipped checks:', '', '| Check | Name | Status | Runs on today | Providers the research adds |', '|---|---|---|---|---|']
        for k in ex:
            c = existing[k]
            st = 'running' if set(c['implementations']) & running_prov else 'planned'
            add = extmap.get(k, {}).get('add_implementations', {})
            extra = ''
            if extmap.get(k, {}).get('aliases'):
                extra = ' Aliases: ' + ', '.join(f'`{a}`' for a in extmap[k]['aliases']) + '.'
            L.append(f"| `{k}` | {esc(c['name'])} | {st} | {', '.join(c['implementations']) or 'none'} | {', '.join(f'{p} {lvl[l]}' for p, l in add.items()) or 'none'}{extra} |")
        L.append('')
    if pr:
        L += ['Proposed checks:', '', '| Check | Name | Providers | Controls | Aliases |', '|---|---|---|---|---|']
        for k in pr:
            c = proposed[k]
            L.append(f"| `{k}` | {esc(c['name'])} | {provs(c)} | {ctls(c)} | {', '.join(f'`{a}`' for a in c['aliases']) or ''} |")
        L.append('')
    if un:
        L += ['Unresolved needs:', '', '| Need | Entries | Reason |', '|---|---|---|']
        for pred, n in sorted(un.items(), key=lambda x: -x[1]):
            reason, why = unres_why[pred]
            L.append(f"| {esc(pred)} | {n} | {reason.replace('_', ' ')}: {esc(why)} |")
        L.append('')
L += ['## 5.4 Aliases resolved', '',
      'Where researchers wrote the same predicate under different keys, one key stays and the others are recorded as',
      'aliases (they are never created). Canonical keys that are shipped checks are extended in',
      '`checks-proposed.json` under `existing_check_extensions`.', '',
      '| Alias | Canonical key | Why |', '|---|---|---|']
why_alias = {}
for c in P['checks']:
    for a in c['aliases']:
        why_alias[a] = c['key']
for e in P['existing_check_extensions']:
    for a, wy in (e.get('alias_notes') or {}).items():
        L.append(f"| `{a}` | `{e['key']}` (shipped) | {esc(wy)} |")
for c in P['checks']:
    m = re.findall(r'Merged alias (\S+): (.*?)(?= Merged alias |$)', c.get('notes', ''))
    for a, wy in m:
        L.append(f"| `{a}` | `{c['key']}` | {esc(wy)} |")
L += ['', '## 5.5 Similar keys kept apart', '',
      'These look alike but read a different source, population or predicate, so they stay separate checks.', '',
      '| Check | Related to | Why kept apart |', '|---|---|---|']
seenrel = set()
for c in P['checks']:
    for r in c['related']:
        sig = tuple(sorted((c['key'], r['key'])))
        if sig in seenrel:
            continue
        seenrel.add(sig)
        L.append(f"| `{c['key']}` | `{r['key']}` | {esc(r['why'])} |")
L += ['', '## 5.6 Needs resolution', '',
      'Every `NEED <capability>: <predicate>` in `coverage/*.json` was matched to a check key or marked unresolved. Per',
      'entry detail: [coverage/needs-resolution.json](coverage/needs-resolution.json).', '',
      '| Match | Entries | Distinct predicates |', '|---|---|---|']
for m in ('exact', 'partial', 'unresolved'):
    L.append(f"| {m} | {cnts['by_match'].get(m, 0)} | {cnts['unique_by_match'].get(m, 0)} |")
L += [f"| total | {cnts['entries']} | {cnts['unique_predicates']} |", '',
      f"Resolved entries point at a shipped check {cnts['resolved_to_existing']} times and at a proposed check {cnts['resolved_to_proposed']} times.",
      f"Unresolved: {cnts['unresolved_by_reason'].get('not_defined', 0)} because no researcher defined a check, {cnts['unresolved_by_reason'].get('no_provider', 0)} because no researched provider can collect it.", '',
      '| Capability | Exact | Partial | Unresolved |', '|---|---|---|---|']
for cp, v in cnts['by_capability'].items():
    L.append(f"| `{cp}` | {v.get('exact', 0)} | {v.get('partial', 0)} | {v.get('unresolved', 0)} |")
L += ['', 'The largest unresolved need: "every active person on the HR roster has a Verity membership" (13 entries). No',
      'check compares a roster with Verity members, so acknowledgement and training checks only ever see members. It',
      'needs a `verity_members` check on top of `hr.roster_exported`, and the roster source decision (08, people topic).', '',
      'A partial match never satisfies an artifact on its own under rule A; it is listed so the reconciliation step adds',
      'the check as a source with `fills: partial`.', '']
L += ['## 5.7 Coverage downgrades', '',
      'Every proposal to move a mapping from full to partial, gathered from all documents. All 16 full links from a check',
      'to a control in `checks.json` are proposed for partial: no connector check proves a whole control.', '',
      '| Check | Control | Reason | Raised in |', '|---|---|---|---|']
for g in dg_check:
    L.append(f"| `{g['check']}` | {g['control']} | {esc(g.get('reason'))} | {esc('; '.join(sorted(set(s for s in g['sources'] if s))))} |")
L += ['', 'Requirement to control mappings proposed to move from full to partial (they change framework status and need',
      'the qualified reviewer, FW-5):', '', '| Requirement | Control | Reason | Raised in |', '|---|---|---|---|']
for g in dg_req:
    L.append(f"| {g['requirement']} | {g['control']} | {esc(g.get('reason'))} | {esc('; '.join(sorted(set(s for s in g['sources'] if s))))} |")
L += ['', 'Requirements that leave a control for a successor at the same coverage (not a loss, listed because readiness',
      'moves with them):', '', '| Requirement | From | Change | Raised in |', '|---|---|---|---|']
for g in dg_move:
    L.append(f"| {g['requirement']} | {g['control']} | {esc(g.get('to'))}: {esc(g.get('reason'))} | {esc('; '.join(sorted(set(s for s in g['sources'] if s))))} |")
L += ['', 'More requirement mapping changes (adds, removals, the DM-03 raise) are in [06-control-changes.md](06-control-changes.md).', '']

# checks that fill no artifact
named_today = {k for a in artifacts.values() for s in a['sources'] if s['kind'] == 'check' for k in s.get('checks', [])}
named_plan = set(named_today)
for f in CF:
    for e in cov[f]:
        for p in e['planned']:
            if p.get('check'):
                named_plan.add(canon(p['check']))
for r in N['needs']:
    if r.get('check'):
        named_plan.add(r['check'])
for e in P['existing_check_extensions']:
    if e.get('add_artifacts'):
        named_plan.add(e['key'])
ex_none = sorted(k for k in existing if k not in named_plan)
ex_today = sorted(k for k in existing if k not in named_today)
pr_none = sorted(k for k, c in proposed.items() if not c['artifacts'] and k not in named_plan)
L += ['## 5.8 Checks that fill no artifact', '',
      'A check that no artifact names cannot move an objective (01-evidence-model.md 1.2).', '',
      f"- Shipped checks named by no artifact in `artifacts.json` today: {len(ex_today)}. After the coverage plan, the needs",
      f"  resolution and the extensions are applied: {len(ex_none)}" + (': ' + ', '.join(f'`{k}`' for k in ex_none) + '.' if ex_none else '.'),
      f"- Proposed checks with no artifact: {len(pr_none)}" + (': ' + ', '.join(f'`{k}`' for k in pr_none) + '. Each needs an artifact or should be dropped.' if pr_none else '.'), '']
L += ['## 5.9 Conflicts resolved', '',
      '| Conflict | Resolution |', '|---|---|',
      '| `tickets.incidents_registered` and `alerts.incidents_registered` test one reconciliation from two tools; the drafts disagreed on the empty population (insufficient against pass) | One key, `alerts.incidents_registered`, capabilities alerting and ticketing with capability_match each, requires `verity_tasks`. Empty population passes only when the source returned the complete list for the period, otherwise insufficient information (rule 4) |',
      '| Three access list keys (`cloud.`, `vcs.`, `apps.access_list_exported`) and the shipped `idp.access_list_exported`; the cloud and code research asked to keep one key per capability so an identity provider list cannot stand in for the code host list | Folded into the shipped `idp.access_list_exported` (AUTHORING: reuse a key whose meaning fits), with capability_match each so every connected system must produce its own complete list. Control mappings were inconsistent (IAM-02 only; IAM-02, 07, 12; IAM-02, 09): the union is kept, each partial with its own rationale |',
      '| `apps.admins_limited` repeats the shipped `idp.admins_limited` | Folded into `idp.admins_limited` with capability_match each |',
      '| `edge.members_current` (operations) and `apps.members_active_in_directory` (phase 3) | One key, `apps.members_active_in_directory`, capabilities business_applications and network_edge, requires identity_provider |',
      '| Three recurring task keys from three researchers; grace 14 days for every cadence against 2, 7 and 30 days by cadence; one added approval | One key, `verity.tasks.recurring_done_on_time`, grace by cadence as the default, approval where the template requires it |',
      '| Two vendor assurance review keys on different populations (hosting providers on PE-01, critical vendors on BC-08) | One key, `verity.vendors.assurance_report_reviewed`, population is the union |',
      '| `verity.tasks.change_approved_independently` and `verity.tasks.approved_before_done` | One key, `verity.tasks.approved_before_done`; the timing rule becomes a template setting |',
      '| `verity.exceptions.in_force` and `verity.risks.acceptance_independent` read the same risk acceptances | One key, `verity.risks.acceptance_independent`; for a control, the population is that control\'s exceptions |',
      '| Two proposed artifacts for LM-02.C: `log-retention-settings` (operations) and `log-store-retention-and-access-settings` (SD, LM, BC mapping, which also splits the objective) | Keep `log-store-retention-and-access-settings`; the other is its alias |',
      '| Capability names: `business_application` against `business_applications`; `security_training` against `learning_platform` | `business_applications` and `learning_platform`, the names the coverage NEEDs already use |',
      '| Scanners listed as implementations of `verity.vulns.within_sla` and `verity.vulns.kev_owned` | Recorded as feeding the vulnerability register (`fed_by`), not as implementations: the check reads the register |',
      '| 1Password on `idp.access_list_exported` and `idp.sso_enforced`, Intune on `endpoint.protection_active`, outside the check\'s capability | password_manager and device_management added to those checks with capability_match each |',
      '| Scan interval: `scanner.scans_current` 30 days, LM-13.B quarterly, `verity.vulns.assets_scanned` 92 days | Both keys kept (different sources); the default goes to the owner (08) |',
      '| `evidence-logs-are-reviewed`: the AWS research adds `cloud.audit_logging` and `cloud.flow_logs_enabled`, the Azure research keeps it with people | Added as partial sources: under rule A they show the logs exist and never satisfy the review alone |',
      '| `scanner.scans_current` and `verity.vulns.within_sla` after the EP-04 split: the IAM file says both move to NS-13 and also that they stay | Move to NS-13, as the IAM researcher recommends (EP-04 becomes company devices only). `scanner.scans_current` also moves from LM-11 to LM-13 (SD, LM, BC file) |',
      '| `verity.vulns.assets_scanned` was listed as an alias of `scanner.scans_current` | Kept apart (5.5): one reads Verity\'s register, the other the scanner |',
      '| Slack listed under `alerting` | Proposed to leave alerting; it implements no check (operations decision 2) |',
      '| Azure research recommends one shared multi tenant app; Entra and unified setup research recommend customer owned evidence apps first | Not resolved here: an owner decision (08, credentials topic) |',
      '']
w('05-check-registry.md', '\n'.join(L))

# ================================================================================================ 06 control changes
L = ['# 6. Control changes', '',
     'The consolidated breakdown of the three `coverage/*.controls.json` files: what the mapping research proposes to keep,',
     'revise, split and add, with every successor control, the objectives that move or are added, the tenant impact, the',
     'check mappings that must follow a split, the new capabilities proposed anywhere in the research, and the content',
     'defects found. Proposals for qualified review (FW-5), never applied by this plan (AUTHORING section 6).', '',
     '## 6.1 Decisions per control', '', '| File | Keep | Revise objectives | Split | Add | Controls reviewed |', '|---|---|---|---|---|---|']
tot = collections.Counter()
for f in CF:
    c = collections.Counter(e['decision'] for e in ctl[f])
    tot.update(c)
    L.append(f"| `{f}.controls.json` | {c['keep']} | {c['revise_objectives']} | {c['split']} | {c['add']} | {len(ctl[f])} |")
L.append(f"| All | {tot['keep']} | {tot['revise_objectives']} | {tot['split']} | {tot['add']} | {sum(tot.values())} |")
L += ['', f"133 shipped controls reviewed; {tot['split']} splits create {tot['split']} successors and {tot['add']} controls are added, so the library would hold {133 + tot['split'] + tot['add']}. No merge or deprecation is proposed.", '']
oc = collections.Counter(o['change'] for o in all_obj_changes)
L += [f"Objective changes: {oc['add']} added, {oc['reword']} reworded, {oc['move']} moved" + (f", {oc['remove']} removed" if oc['remove'] else '') + '. A move is listed once on its source control (SD-15 also lists SD-05.D as moved in).', '']

def reqtable(reqs):
    out = ['| Requirement | Coverage | Rationale |', '|---|---|---|']
    for r in reqs:
        out.append(f"| {r.get('key') or r.get('requirement_key')} | {r['coverage']} | {esc(r.get('rationale'))} |")
    return out

L += ['## 6.2 Splits', '']
for f in CF:
    for e in ctl[f]:
        if e['decision'] != 'split':
            continue
        for s in e['successors']:
            L += [f"### {e['control']} {esc(templates[e['control']]['name'])} to {s['code']} {esc(s['name'])}", '',
                  f"Reason: {esc(e['reason'])}", '']
            meta = []
            if s.get('owner_function'):
                meta.append(f"owner {s['owner_function']}")
            if s.get('applies_when'):
                aw = esc(s['applies_when']).rstrip('.')
                meta.append(f"applies when {aw[:1].lower() + aw[1:]}")
            if meta:
                L += ['Successor: ' + '; '.join(meta) + '.', '']
            L += [f"Objectives taken from {e['control']}: {', '.join(s.get('takes_objectives') or []) or 'none'}. New objectives: {', '.join(s.get('new_objectives') or [o['code'] for o in e['objective_changes'] if o['change'] == 'add' and o['code'].startswith(s['code'] + '.')]) or 'none'}.", '']
            L += reqtable(s.get('requirements', [])) + ['', f"Tenant impact: {esc(e['tenant_impact'])}", '']
L += ['## 6.3 Additions', '']
for code, s in succ.items():
    if s['decision'] != 'add':
        continue
    e = next(x for f in CF for x in ctl[f] if x['control'] == code)
    L += [f"### {code} {esc(s['name'])}", '', f"Reason: {esc(e['reason'])}", '']
    if s.get('owner') or s.get('applies_when'):
        L += [f"Owner {s.get('owner') or 'not stated'}; applies when {esc(s.get('applies_when') or 'not stated')}.", '']
    L += [f"Objectives: {', '.join(o['code'] for o in e['objective_changes'] if o['change'] in ('add', 'move')) or 'none'}.", '']
    L += reqtable(s['requirements']) + ['', f"Tenant impact: {esc(s['tenant_impact'])}", '']
L += ['## 6.4 Objectives revised on kept controls', '', '| Control | Changes | Objectives | Tenant impact |', '|---|---|---|---|']
for f in CF:
    for e in ctl[f]:
        if e['decision'] == 'revise_objectives':
            ch = collections.Counter(o['change'] for o in e['objective_changes'])
            L.append(f"| {e['control']} | {', '.join(f'{v} {k}' for k, v in ch.items())} | {', '.join(o['code'] for o in e['objective_changes'])} | {esc(e['tenant_impact'])} |")
L += ['', '## 6.5 Objectives moved or added', '', '| Objective | Change | On control | Assurance | Statement | Why |', '|---|---|---|---|---|---|']
for o in all_obj_changes:
    if o['change'] in ('add', 'move'):
        st = o.get('statement') or ''
        tgt = o.get('to') or o['code']
        chg = f"move to {o['to']}" if o['change'] == 'move' and o.get('to') else ('moved in from ' + o['moved_from'] if o.get('moved_from') else o['change'])
        L.append(f"| {o['code']} | {chg} | {tgt.rsplit('.', 1)[0]} | {o.get('assurance', '')} | {esc(st)} | {esc(o.get('why'))} |")
L += ['', 'Reworded objectives are listed per control in the `*.controls.json` files; rewording needs no data migration, but a',
      'reworded objective with an open not applicable decision goes back to the owner to confirm.', '']
L += ['## 6.6 Requirement mapping changes', '', '| Requirement | Control | Change | Coverage now | Rationale | File |', '|---|---|---|---|---|---|']
for f in CF:
    for e in ctl[f]:
        for m in e.get('mapping_changes', []):
            req = m.get('requirement') or m.get('key')
            change = m.get('change') or ('coverage' if m.get('was') and m.get('coverage') not in ('removed',) else m.get('to_coverage') or m.get('coverage'))
            frm = m.get('from_coverage') or m.get('was') or ''
            to = m.get('to_coverage') or m.get('coverage') or ''
            L.append(f"| {req} | {m.get('control', e['control'])} | {esc(change)} | {frm} to {to} | {esc(m.get('rationale'))} | {f} |")
L += ['']

# check mappings that must move
split_ctl = {e['control']: [s['code'] for s in e['successors'] if s['code'] != e['control']] for f in CF for e in ctl[f] if e['decision'] == 'split'}
moves = []
for f in CF:
    for e in ctl[f]:
        for m in e.get('check_mapping_changes', []):
            if 'to_control' in m:
                moves.append((m['check'], m['from_control'], m['to_control'], m.get('why'), f'{f}.controls.json'))
            elif m.get('control') in succ and succ[m['control']]['origin'] == e['control']:
                moves.append((m['check'], e['control'], m['control'], m.get('rationale'), f'{f}.controls.json'))
for e in P['existing_check_extensions']:
    for ch in e.get('changes', []):
        if ch.get('change') == 'move_to_successor' and ch.get('to_control'):
            moves.append((e['key'], ch.get('control'), ch['to_control'], ch.get('rationale'), ch.get('source', '')))
manual = [
    ('scanner.scans_current', 'EP-04', 'NS-13', 'EP-04 becomes company devices only; server and image scanning is NS-13 (IAM decision on the EP-04 split).', 'iam-ep-pe-ns-dm.controls.json EP-04'),
    ('verity.vulns.within_sla', 'EP-04', 'NS-13', 'Same reason; the IAM file contradicts itself and recommends the move.', 'iam-ep-pe-ns-dm.controls.json EP-04'),
    ('verity.assets.disposal_recorded', 'DM-16', 'EP-08', 'Equipment disposal records move to EP-08; the file calls it an owner decision.', 'iam-ep-pe-ns-dm.controls.json DM-16'),
    ('vcs.dependency_alerts_enabled', 'LM-11', 'LM-13', 'Reading of the SD, LM, BC extractor; the document does not name it. It stays on SD-03.', 'sd-lm-bc.md (extractor reading)'),
]
seenm = set()
L += ['## 6.7 Check mappings that must follow a split', '',
      'Shipped `checks.json` mappings on a split control, and where each goes. "Stays" means nothing in the research moves it.', '',
      '| Check | From | To | Why | Source |', '|---|---|---|---|---|']
for mv in moves + manual:
    sig = (canon(mv[0]), mv[1], mv[2])
    if sig in seenm:
        continue
    seenm.add(sig)
    k0 = canon(mv[0])
    on_from = k0 in existing and any(m['code'] == mv[1] for m in existing[k0]['controls'])
    L.append(f"| `{k0}` | {mv[1]} | {mv[2]} ({'move' if on_from else 'add, not mapped to ' + mv[1] + ' today'}) | {esc(mv[3])} | {esc(mv[4])} |")
for code, scs in split_ctl.items():
    for k, c in sorted(existing.items()):
        for m in c['controls']:
            if m['code'] == code and not any(s[0] == k and s[1] == code for s in seenm):
                L.append(f"| `{k}` | {code} | stays on {code} | {esc(m['rationale'])} | checks.json |")
L += ['', 'Proposed checks are already mapped to the successor codes where the researchers intended it (for example',
      '`verity.vulns.assets_scanned` to LM-13, `verity.tasks.approved_before_done` to SD-17 and SD-18). Existing workspaces',
      'never inherit a green result, a check history or a risk acceptance on a successor: each successor is an adoption',
      'proposal a person confirms, with an audit row (IAM file, What existing workspaces need).', '']

# capabilities
L += ['## 6.8 New capabilities proposed', '',
      '| Capability | What it is for | Providers named | Raised in |', '|---|---|---|---|',
      '| `business_applications` | Software services staff sign in to that hold company or customer data, outside the other capabilities: access lists, admins, single sign on and two factor, member currency, API keys; also consent tools, support desks and finance or payment systems | hubspot, intercom, zendesk, posthog, sendgrid, resend, openai, anthropic; the tools of other capabilities for their own member lists (slack, sentry, datadog, pagerduty, jira, cloudflare, tailscale, grafana, linear, asana, notion and the platforms) | phase3-catalogue.md 1.1; coverage/iam-ep-pe-ns-dm.md; operations-checks.md section 6 (as business_application) |',
      '| `ai_providers` | Services that run AI models on company data: whether retention matches the vendor review, and whether every project and key with usage is owned (`ai.*`) | openai, anthropic | phase3-catalogue.md 1.1 |',
      '| `verity_identity` | Verity\'s own sign in, session audit rows and directory sync as evidence for one application, Verity itself (`verity.identity.*`) | verity | coverage/iam-ep-pe-ns-dm.md |',
      '| `verity_members` | Members, groups and owner functions kept in Verity: leavers\' records handed over, owner functions held (`verity.members.*`) | verity | coverage/gov-cs-hr.md |',
      '| `learning_platform` | The training platform that assigns courses and records completion, overdue assignments and reminders (HR-08, HR-09). Named `security_training` in the device and HR research | none named | coverage/gov-cs-hr.md; mdm-and-endpoint-strategy.md D-HR-4 |',
      '| `esignature` | The signing tool that holds signed confidentiality and IP agreements (HR-02, HR-03) | docusign | coverage/gov-cs-hr.md |',
      '| `background_screening` | The screening provider: completed, cleared checks dated before first access, for hires, moves into sensitive roles and rechecks (HR-01) | checkr, certn | coverage/gov-cs-hr.md; mdm-and-endpoint-strategy.md D-HR-4 |',
      '| `public_web` | Unauthenticated reads of the company\'s own public pages: security.txt, security page, terms, service levels and privacy notice, with changes dated (CS-02, CS-03) | none (Verity reads the pages) | coverage/gov-cs-hr.md |',
      '| `productivity_suite` | Mail and file suite settings: external sharing, public links, leak prevention rules and alerts, sensitivity labels (DM-04, DM-19). Today filed under identity_provider; the owner decides | gws, entra (Microsoft 365) | coverage/iam-ep-pe-ns-dm.md |',
      '| `verity_notifications` | Verity\'s delivery log of the security messages it sent (channel, time, provider message id), for CS-04.D and CS-06.B | verity | operations-checks.md section 6 (inferred) |',
      '']
L += ['Changes proposed to existing capabilities:', '', '| Capability | Change | Raised in |', '|---|---|---|',
      '| `alerting` | Remove Slack (no schedule, escalation or acknowledgement); add Better Stack and Grafana | operations-checks.md section 2; phase3-catalogue.md 1.1 |',
      '| `asset_discovery` | Add the scanners (Tenable, Rapid7, Qualys), DigitalOcean, and the MDMs (Intune, Jamf, Kandji, Google) as device sources | phase3-catalogue.md 1.1; mdm-and-endpoint-strategy.md |',
      '| `ci_cd` | Add Vercel, Netlify, Render, Heroku and Qovery | phase3-catalogue.md 1.1 |',
      '| `cloud_infrastructure` | Qovery is listed but the research gives it ci_cd and business_applications only | phase3-catalogue.md (extractor finding) |',
      '| `network_edge` | Add Vercel (firewall, partial); Tailscale must not implement `edge.minimum_tls` (WireGuard, not TLS) | phase3-catalogue.md; operations-checks.md section 2 |',
      '| `ticketing` | Notion as a business application only (D-P3-5) | phase3-catalogue.md |',
      '| `device_management` | Add Google Workspace (endpoint management and Endpoint Verification); show Kandji as Iru (Kandji) | mdm-and-endpoint-strategy.md D-DEV-11, D-DEV-13 |',
      '| `endpoint_protection` | Add Microsoft Defender for Endpoint and Jamf Protect | mdm-and-endpoint-strategy.md D-DEV-12 |',
      '| `hr_system` | Add HiBob and a CSV roster import (`roster_import`) as the interim source | mdm-and-endpoint-strategy.md D-HR-1; hr-systems.md |',
      '| `password_manager`, `device_management` | Added to `idp.access_list_exported`, `idp.sso_enforced` and `endpoint.protection_active`, where 1Password and Intune implement them | this reconciliation (05, 5.9) |',
      '']
newprov = collections.OrderedDict()
for p in MG['providers_proposed']:
    newprov.setdefault(p['key'], p)
L += ['New provider keys proposed:', '', '| Key | Name | Capability | Phase |', '|---|---|---|---|']
for k, p in newprov.items():
    L.append(f"| `{k}` | {esc(p.get('name'))} | {esc(p.get('capability'))} | {esc(p.get('phase'))} |")
L += ['', 'New observation types the proposed checks need (01-evidence-model.md 1.4 lists the rest): ' + ', '.join(f'`{o}`' for o in P['observation_types_added']) + '.', '']

# proposed artifacts
L += ['## 6.9 Proposed artifacts', '', '| Artifact | Control | Objectives | Why | Raised in |', '|---|---|---|---|---|']
for a in P['artifacts_proposed']:
    al = f" (alias `{', '.join(a['aliases'])}`)" if a.get('aliases') else ''
    L.append(f"| `{a['key']}`{al} | {a.get('control')} | {', '.join(a.get('objectives') or [])} | {esc(a.get('why'))} | {esc('; '.join(s for s in a['sources_docs'] if s))} |")
L.append('')

# defects
# full defect table
seen = {}
for d in MG['defects']:
    item = esc(d.get('item'))
    sig = (d.get('kind'), item.lower(), esc(d.get('finding'))[:70].lower())
    if sig in seen:
        seen[sig]['src'].add(d.get('source') or d['_part'])
        continue
    seen[sig] = {'d': d, 'src': {d.get('source') or d['_part']}}
templ_rows = [v for v in seen.values() if v['d'].get('kind') == 'artifact' and 'template' in (v['d'].get('finding') or '').lower()]
other_rows = [v for v in seen.values() if v not in templ_rows]
tkeys = sorted({t['key'] for t in J(C + 'policies/document_templates.json')}, key=len, reverse=True)
tgroup = collections.OrderedDict()
for v in sorted(templ_rows, key=lambda v: esc(v['d'].get('item'))):
    d = v['d']
    item = esc(d.get('item'))
    txt = (d.get('finding') or '') + ' ' + (d.get('proposal') or '')
    g = tgroup.setdefault(item, {'t': set(), 'c': set(), 'dup': set(), 'src': set()})
    body = re.sub(r'doc-[a-z0-9-]+', ' ', txt)
    for tk in tkeys:
        if re.search(r'(?<![a-z0-9-])' + re.escape(tk) + r'(?![a-z0-9-])', body):
            g['t'].add(tk)
    g['c'].update(re.findall(r'(?<![A-Z-])[A-Z]{2,3}-\d{2}(?!\d)', txt))
    g['dup'].update(re.findall(r'doc-[a-z0-9-]+', txt))
    g['src'].update(re.sub(r' .*', '', s) for s in v['src'] if s)
nop_check = sorted(k for k, a in artifacts.items() if not any(s['kind'] == 'person' for s in a['sources']) and not k.startswith('doc-'))
L += ['## 6.10 Content defects', '',
      'Found by the researchers in shipped content, with what the reconciliation step should do. The most important first;',
      'the full deduplicated list follows.', '',
      '| Defect | Fix |', '|---|---|',
      '| `inventory-of-company-devices` is named by 11 objectives (DM-19.C, EP-01.B, EP-02.B to D, EP-03.B to D, EP-05.B, EP-06.B, EP-07.B), its only source is `devices.enrolled`, it has no person source, and its "where" points at Assets, which has no device type. A passing enrolment check would satisfy encryption, agent, wipe and lock objectives, and a company without an MDM can never satisfy it | Split by what is tested into `device-encryption-report`, `device-protection-agent-report` and `device-wipe-capability-report`, each with its device check and a person source; add a device type to Assets. EP-02.D and EP-03.D have no home in the split yet |',
      f"| {len(nop_check)} non document artifacts have no person source, against rule 1 of the evidence model: " + ', '.join(f'`{k}`' for k in nop_check) + ' | Add `{"kind": "person"}` to each, or record why a person can never provide it |',
      '| Four person only document artifacts duplicate a `doc-` artifact on the same objective (`change-management-policy` on SD-01.A, `secure-development-lifecycle-policy` on SD-10.A, `incident-response-plan` on LM-07.A, `business-continuity-and-disaster-recovery-plan` on BC-03.A and B) | Fold each into its `doc-` artifact |',
      f'| {len(tgroup)} document artifacts list only a person, although a shipped template holds the text (full list below) | Give each a document source with its template, or fold it into the `doc-` artifact (owner decision, 08) |',
      '| Template gaps: missing sections in `access-control-policy`, `third-party-management-policy`, `cryptography-policy`, `endpoint-security-standard`, `engineering-security-standard` (also needs a product sign in section for IAM-14); no template at all for a vulnerability management policy, a backup policy, a subprocessor list or a postmortem | CL-6 template work, or point the objectives at existing sections |',
      '| Checks that reach no artifact, so they cannot move any objective: see 05, 5.8. Shipped examples: `idp.mfa_enforced`, `idp.sso_enforced`, `vcs.org_two_factor_required`, `devices.disk_encrypted`, `devices.screen_lock`, `devices.remote_wipe`, `endpoint.protection_active` | Add them as sources of the artifacts named in the coverage files |',
      '| Artifacts listing only a person though a check exists: `screen-lock-setting-report` (`devices.screen_lock`), `privileged-elevation-and-break-glass-log` (`idp.admins_limited`), `second-factor-enforcement-and-enrolled-users` (`idp.mfa_enforced`), `control-test-results-across-the-observation` (check run history) | Add the check as a source; keep the person |',
      '| `roster-of-joiners-and-leavers-with` is sourced by `people.leavers_deprovisioned`, an account removal check that covers leavers only | Source it from `hr.roster_exported` and `people.joiners_onboarded`; keep the person |',
      '| `management-review-agenda-and-minutes` is given different sources on GOV-15 and GOV-31, which `artifacts.json` cannot express | Split into a quarterly and a yearly artifact |',
      '| `branch-protection-settings` on SD-02.B lacks `vcs.status_checks_required` | Add it |',
      '| `access-request-procedure` (DM-11, a data subject request procedure) sits beside `access-request-and-approval-procedure` (IAM) | Rename to "data-subject-access-request-procedure", with an evidence migration |',
      '| `management-review-agenda-and-minutes` and `internal-audit-or-readiness-assessment-report` are typed configuration | Type them as records |',
      '| `MANAGEMENT_REVIEW_INPUTS` labels follow the standard\'s list too closely | Rewrite in Verity\'s words |',
      '| `capabilities.json`: Slack under alerting; Qovery under cloud infrastructure; DigitalOcean missing from asset discovery; HR and device providers `not_planned` while LM-01 text and the coverage files rely on them | See 6.8 |',
      '| Module gaps found in code: the vulnerability register matches assets loosely, drops unmatched findings, lacks first found time, explicit severity maps, scanner verified closure and `external_id`; the GitHub connector reports error instead of insufficient information on a truncated population; Tasks has no incident kind and task templates are not bound to controls; Assets has no device type; assurance records need an engagement; ISO certificates have no structured period fields | Fix before the checks that depend on them ship (phase3-catalogue.md 5.2, D-P3-2) |',
      '']
L += [f"### Full list ({len(seen)} findings after removing exact repeats)", '',
      f"Document artifacts that list only a person although a template holds the text ({len(tgroup)} artifacts). Fix: add a",
      '`document` source for the template (and section), or fold the artifact into the `doc-` artifact named on the same objective.', '',
      '| Artifact | Template holding the text | Controls | Same objective also names | Raised in |', '|---|---|---|---|---|']
for item, g in tgroup.items():
    L.append(f"| {item} | {', '.join(sorted(g['t'])) or 'see finding in the coverage file'} | {', '.join(sorted(g['c']))} | {', '.join(sorted(g['dup']))} | {', '.join(sorted(g['src']))} |")
L += ['', 'Other defects, by kind:', '']
for kind in ('artifact', 'check', 'mapping', 'objective', 'template', 'capability', 'provider', 'module', 'other'):
    rs = [v for v in other_rows if v['d'].get('kind') == kind]
    if not rs:
        continue
    L += [f"#### {kind.capitalize()} ({len(rs)})", '', '| Item | Finding | Proposal | Source |', '|---|---|---|---|']
    for v in sorted(rs, key=lambda v: esc(v['d'].get('item'))):
        d = v['d']
        L.append(f"| {esc(d.get('item'))} | {esc(d.get('finding'))} | {esc(d.get('proposal'))} | {esc('; '.join(sorted(s for s in v['src'] if s)))} |")
    L.append('')
w('06-control-changes.md', '\n'.join(L))

# ================================================================================================ 08 decisions
dec = MG['decisions']  # same order as decisions_dump.txt (sorted parts)
TOPIC = {}
groups = {
    'A': ('Scope, catalogue and build order', [1, 14, 17, 27, 28, 38, 39, 40, 60, 79, 83, 85, 86, 94]),
    'B': ('Credentials and connection model', [2, 3, 5, 6, 7, 9, 11, 13, 15, 16, 18, 19, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 61, 64, 66, 72, 81, 82]),
    'C': ('Coverage honesty and plan limits', [4, 8, 10, 48, 49, 73, 108, 109, 110]),
    'D': ('Check definitions and default thresholds', [12, 35, 36, 45, 46, 70, 71, 95, 141, 143, 144]),
    'E': ('Artifacts, templates and content fixes', [20, 21, 22, 23, 24, 25, 26, 32, 69, 96, 117, 118, 122, 139, 142]),
    'F': ('Control splits, additions and objectives', [87, 88, 89, 90, 91, 92, 103, 104, 105, 106, 107, 111, 112, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 145]),
    'G': ('People, HR and devices without a connected system', [62, 42, 43, 29, 37, 34, 97, 99]),
    'H': ('Verity modules and data', [33, 80, 84, 100, 67, 101, 102, 119, 120, 65]),
    'I': ('Other', [74, 75]),
}
MERGE = {4: [31, 63, 68, 113], 27: [114], 29: [30, 77], 33: [121], 42: [76], 43: [98], 47: [78], 62: [41, 93, 115], 79: [116], 94: [44], 100: [123, 140]}
OVERRIDE = {
    4: ('Coverage downgrades', 'Approve moving all 16 full check to control mappings in checks.json to partial (cloud: NS-01, NS-08, LM-03, SD-12; devices and endpoint: EP-01, EP-02, EP-03, EP-06; identity: IAM-04, IAM-05, IAM-06, IAM-11, IAM-12; operations: IAM-01, NS-10, NS-11), each with a rationale naming what remains. List in 05-check-registry.md 5.7.', 'Approve all 16 (authoring rule 5): no connector check proves a whole control, and the current rationale "which is what the control states" fails EC-3.'),
    62: ('Staff roster source', 'Verity members are not the staff list, no HR connector is in a signed phase, and every check that needs a staff, leaver or contractor roster reads insufficient information until one exists (people.*, vault.*, acknowledgement, training, joiner checks; IAM-01, IAM-05, IAM-12, EP-03, EP-05, NS-11, PE-02, HR family). Choose the roster source.', 'Build the CSV roster import (provider roster_import) as the interim HR source; it is the proposed reading of control-framework-requirements open question 1.'),
    29: ('Endpoint agent and customers without an MDM', 'Should Verity build or adopt an endpoint agent (Go plus osquery, or Fleet as a base) for customers without an MDM, or rely on Google Endpoint Verification, Intune and reviewed attestation? EP-02, EP-03, EP-05 and EP-06 can only be satisfied by people today.', 'Do not build an agent now. Use Google Endpoint Verification where the customer runs Google Workspace and Intune where they run Microsoft; re-decide when paying customers without an MDM are a meaningful share. If built: Go plus osquery, with the query list public, decided in an ADR.'),
}
NOTES = {6: 'Conflict: entra-id.md and identity-providers-unified-setup.md recommend customer owned evidence apps first and Verity\'s multi tenant app only after the first Entra pilot (decision on Entra evidence app ownership below). Decide both together.',
         47: 'Conflict: azure.md (D-AZ-1) recommends one shared multi tenant app for Azure and Entra ID. Decide both together.',
         144: 'Found during reconciliation; no document raises it. Both keys stay (05, 5.5).'}
assigned = {i for g in groups.values() for i in g[1]} | {i for v in MERGE.values() for i in v}
missing = set(range(1, len(dec) + 1)) - assigned
assert not missing, missing
L = ['# 8. Owner decisions (raw)', '',
     'Every decision for the owner raised in any research document, deduplicated and grouped by topic. Each entry names',
     'the document it came from and the researcher\'s recommendation. "Raw": not yet ordered by urgency; the phase',
     'plan picks from here. Where two documents raised the same question, the entry lists both sources.', '',
     f"{len(dec)} questions raised; {len(dec) - sum(len(v) for v in MERGE.values())} after merging duplicates.", '']
n = 0
for gk, (title, idx) in groups.items():
    L += [f'## 8.{list(groups).index(gk) + 1} {title}', '', '| # | Decision | Recommendation | Raised in |', '|---|---|---|---|']
    for i in idx:
        d = dec[i - 1]
        topic, q, rec = d.get('topic'), d.get('question'), d.get('recommendation')
        srcs = [d.get('source')]
        for j in MERGE.get(i, []):
            srcs.append(dec[j - 1].get('source'))
            if not rec:
                rec = dec[j - 1].get('recommendation')
        if i in OVERRIDE:
            topic, q, rec = OVERRIDE[i]
        n += 1
        note = NOTES.get(i, '')
        opts = d.get('options') or []
        opt = (' Options: ' + '; '.join(esc(o) for o in opts) + '.') if opts and i not in OVERRIDE else ''
        L.append(f"| {n} | **{esc(topic)}.** {esc(q)}{opt}{(' ' + esc(note)) if note else ''} | {esc(rec) or 'none given'} | {esc('; '.join(dedupe for dedupe in dict.fromkeys(s for s in srcs if s)))} |")
    L.append('')
L.append(f'{n} decisions listed.')
w('08-owner-decisions-raw.md', '\n'.join(L) + '\n')
print('docs written', n, 'decisions;', len(rows), 'matrix rows;', len(seen), 'defects')
