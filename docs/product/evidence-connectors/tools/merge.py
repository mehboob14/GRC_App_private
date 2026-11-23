import os
"""Merge the extraction parts into checks-proposed.json and coverage/needs-resolution.json.
Also writes merged.json (scratch) for the markdown generator. Run: PYTHONUTF8=1 python merge.py"""
import json, glob, collections, copy, re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from needs_map import M as NEEDS_MAP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')).replace(os.sep, '/')
DOCS = ROOT + '/docs/product/evidence-connectors/'
C = ROOT + '/backend/src/verity/seed/content/'
J = lambda p: json.load(open(p, encoding='utf-8'))

existing = {c['key']: c for c in J(C + 'automation/checks.json')}
caps = J(C + 'automation/capabilities.json')
cap_providers = {c['key']: {p['key']: p for p in c['providers']} for c in caps}
artifacts = {a['key']: a for a in J(C + 'objectives/artifacts.json')}
parts = {os.path.basename(f)[:-5]: J(f) for f in sorted(glob.glob(HERE + '/parts/*.json'))}

# ---------------------------------------------------------------- aliases
ALIASES = {
    'tickets.incidents_registered': 'alerts.incidents_registered',
    'cloud.access_list_exported': 'idp.access_list_exported',
    'vcs.access_list_exported': 'idp.access_list_exported',
    'apps.access_list_exported': 'idp.access_list_exported',
    'apps.admins_limited': 'idp.admins_limited',
    'edge.members_current': 'apps.members_active_in_directory',
    'verity.tasks.reviews_on_cadence': 'verity.tasks.recurring_done_on_time',
    'verity.tasks.recurring_review_on_time': 'verity.tasks.recurring_done_on_time',
    'verity.vendors.assurance_reviewed': 'verity.vendors.assurance_report_reviewed',
    'verity.tasks.change_approved_independently': 'verity.tasks.approved_before_done',
    'verity.exceptions.in_force': 'verity.risks.acceptance_independent',
}
ALIAS_WHY = {
    'tickets.incidents_registered': 'Same reconciliation (every incident in a source tool is in the Verity register or has a not an incident decision) from a ticketing source. Kept the alerting key, as the operations research recommended: incidents are the native object there.',
    'cloud.access_list_exported': 'Same predicate (the complete, dated list of accounts and roles was read for every in scope account) on cloud infrastructure.',
    'vcs.access_list_exported': 'Same predicate on version control (members, owners, outside collaborators, repository admins).',
    'apps.access_list_exported': 'Same predicate on a business application (members, guests, pending invites).',
    'apps.admins_limited': 'Same predicate as idp.admins_limited (admin roles held only by named, approved people) on a business application.',
    'edge.members_current': 'Same predicate (every active member of a tool is an active identity provider user, or a recorded external or service member) on the remote access tool. apps.members_active_in_directory is the more general wording.',
    'verity.tasks.reviews_on_cadence': 'Three researchers wrote the same predicate on recurring task series linked to a control. Kept the most general key; approval where the template requires it is folded in.',
    'verity.tasks.recurring_review_on_time': 'Same predicate on recurring task series; its per cadence grace (2, 7, 30 days) becomes the default grace parameter.',
    'verity.vendors.assurance_reviewed': 'Same predicate (a current assurance report reviewed by a named person within 12 months, customer controls marked reviewed) on hosting providers linked to PE-01. Population widened to critical vendors plus vendors linked to a control as a hosting provider.',
    'verity.tasks.change_approved_independently': 'Same predicate (a task from a template that requires approval was approved by an active member who is neither its owner nor an assignee) for change templates. The timing rule (before work, before resolution, or within a window after an emergency change) becomes a template setting.',
    'verity.exceptions.in_force': 'Same records and predicate (risk acceptances approved by someone other than the requester, with a reason and an expiry) for acceptances recorded as exceptions to a control. When the check runs for a control, the population is that control\'s exceptions.',
}
CANON_PATCH = {
    'alerts.incidents_registered': {
        'capabilities': ['alerting', 'ticketing'], 'capability_match': 'each', 'requires': ['verity_tasks'],
        'name': 'Incidents in source tools are in the register',
        'description': 'Every security or major incident raised in a connected on call or ticketing tool appears in Verity\'s incident register, or has a recorded decision there that it was not a security incident.',
        'empty_population': 'pass only when the source returned the complete incident list for the period; otherwise insufficient information. Conflict resolved: the Jira draft read insufficient on an empty list, the PagerDuty draft passed; the rule above keeps rule 4 of the evidence model for both.',
    },
    'apps.members_active_in_directory': {
        'capabilities': ['business_applications', 'network_edge'], 'capability_match': 'each', 'requires': ['identity_provider'],
    },
    'verity.tasks.recurring_done_on_time': {
        'name': 'Recurring compliance work is done on time',
        'description': 'Every occurrence of a recurring task series linked to the control and due in the period was closed by an active member within its grace, with a note or an attachment, and approved where its template requires approval.',
        'predicate': 'Each occurrence was closed, not cancelled, by its due date plus the grace, with a closing note or an attachment; where the template requires approval it was approved by an active member who is not its owner or assignee. A cancelled occurrence counts as missed.',
        'parameters': {'grace_days': 'default by cadence: weekly 2, monthly or quarterly 7, annual 30 (from verity.tasks.recurring_review_on_time); a series may set its own, the gov draft used 14 for every cadence'},
    },
    'verity.vendors.assurance_report_reviewed': {
        'population': 'Approved vendors of tier critical with a live engagement, plus every active vendor linked to a control as a hosting provider (for example PE-01).',
    },
    'verity.tasks.approved_before_done': {
        'description': 'Every task from a template that requires approval (access request, privileged access, new use of personal data, change, emergency change, production data change, licence exception) was approved by an active member who is neither its reporter, owner nor an assignee, at the time its template requires.',
        'parameters': {'approval_timing': 'per template: before work starts (SD-17, SD-18), before resolution (access requests), or within a window after resolution for emergency changes (SD-04, default next business day)'},
    },
    'verity.risks.acceptance_independent': {
        'description': 'Every risk acceptance decided in the last 12 months, and every acceptance recorded as an exception to a control and still in force, was approved by an active member other than the requester, with a reason, a safeguard where it is a control exception, and an expiry that has not passed.',
    },
}
# Related, not aliases: different source, population or predicate. (key, related keys, why)
RELATED = [
    ('verity.vulns.assets_scanned', ['scanner.scans_current'], 'Same aim from a different source: Verity\'s register of imported scans against Assets, versus the scanner\'s own history. Kept apart; the scan interval default conflicts (92 against 30 days) and goes to the owner.'),
    ('verity.vulns.closed_within_sla', ['verity.vulns.within_sla'], 'Period view of fixes made, against the state of open findings now.'),
    ('verity.vulns.kev_triaged_same_day', ['verity.vulns.kev_owned'], 'Triage time against ownership; share the triage logic.'),
    ('verity.incidents.registered', ['alerts.incidents_registered'], 'Facts in each register entry, against completeness of the register against a source tool.'),
    ('verity.incidents.postmortem_recorded', ['alerts.postmortems_completed'], 'Same aim, different record: the postmortem in Verity Tasks with actions, against the review status in the on call tool.'),
    ('vault.leavers_removed', ['people.leavers_deprovisioned'], 'Same leaver population and removal time, on the password manager instead of the identity provider.'),
    ('cloud.human_users_mfa', ['idp.mfa_enforced', 'cloud.root_account_mfa'], 'Local cloud users outside the identity provider; root is its own check.'),
    ('apps.mfa_enforced', ['idp.mfa_enforced', 'vcs.org_two_factor_required'], 'Accepts per member two factor, which a policy check does not.'),
    ('apps.sso_enforced', ['idp.sso_enforced'], 'Read from the application side, which an identity provider cannot see.'),
    ('cloud.secrets_rotated', ['cloud.secrets_managed', 'cloud.machine_credentials_rotated'], 'Different population, age limit and controls.'),
    ('ci.production_deploys_approved', ['ci.production_deploys_controlled'], 'Practice per deployment against the setting.'),
    ('vcs.dependency_alerts_within_sla', ['verity.vulns.within_sla'], 'Owner decision D-GH-2: judge alerts in GitHub now, import them into the register later.'),
    ('verity.tasks.capa_on_time', ['verity.tasks.remediation_in_sla', 'verity.assurance.findings_tracked', 'verity.tasks.owned_and_dated'], 'Different populations: corrective actions of issues and incidents, assurance findings, all linked tasks.'),
    ('verity.vulns.acceptances_approved', ['verity.risks.acceptance_independent'], 'Finding acceptances in Vulnerabilities, not risk acceptances.'),
    ('verity.assurance.internal_audit_held', ['verity.audit.internal_in_12_months'], 'Adds independence of the performer.'),
    ('verity.assurance.management_review_held', ['verity.management_review.in_12_months'], 'Quarterly cadence; the 12 month check moves to GOV-31.'),
    ('verity.policies.acknowledged_at_join', ['verity.policies.acknowledged'], 'Joiners within days of joining, against the annual population.'),
    ('verity.vendors.breach_terms_recorded', ['verity.vendors.security_terms_on_file'], 'Vendors holding personal data and the breach notice field only, against critical and high vendors and every security term.'),
    ('verity.vendors.personal_data_recorded', ['verity.vendors.subprocessor_list_current'], 'The record fields, against the published list matching them.'),
    ('hr.training_current', ['verity.training.acknowledged'], 'Training in the HR system against in house material acknowledged in Verity.'),
    ('verity.tasks.checklist_steps_done', ['people.joiners_onboarded'], 'Checklist steps in Verity against accounts created at the identity provider.'),
    ('idp.no_inactive_accounts', ['cloud.unused_credentials_disabled'], 'User accounts against cloud passwords and access keys.'),
    ('verity.risks.acceptance_independent', ['verity.risks.acceptance_current'], 'Independence, reason and expiry, against an acceptance in date.'),
]
OBS_FILL = {
    'idp.access_reviews_completed': ['identity.access_review'],
    'alerts.on_call_covered': ['escalation_policy', 'on_call_entry'],
    'alerts.escalation_policies_escalate': ['escalation_policy', 'service'],
    'observability.siem_rules_enabled': ['detection_rule'],
    'observability.security_signals_triaged': ['security_signal'],
    'observability.audit_trail_enabled': ['audit_event'],
    'observability.errors_triaged_in_time': ['error_issue'],
    'scanner.authenticated_scans': ['scanner.scan', 'scanner.asset'],
    'apps.sso_enforced': ['app.setting', 'app.member'],
    'apps.mfa_enforced': ['app.setting', 'app.member'],
    'apps.api_keys_current': ['app.api_key'],
    'ai.retention_matches_review': ['ai.setting', 'verity.record'],
    'ai.usage_attributed': ['ai.usage', 'ai.api_key'],
}
OBS_BASE = {'identity.user', 'identity.policy', 'identity.app', 'identity.event', 'vault.member', 'device', 'person.record',
            'repository', 'branch_rule', 'change', 'review', 'pipeline_run', 'deployment', 'cloud.resource', 'cloud.principal',
            'cloud.credential', 'ticket', 'alert', 'incident', 'monitor', 'edge.zone', 'edge.policy'}
CAP_CANON = {'business_application': 'business_applications', 'security_training': 'learning_platform'}
LEVELS = {'supported': 2, 'partial': 1, 'not_possible': 0}


def dedupe(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def merge_controls(a, b, notes):
    by = {m['code']: m for m in a}
    for m in b:
        if m['code'] not in by:
            by[m['code']] = copy.deepcopy(m)
        elif by[m['code']]['coverage'] != m['coverage']:
            notes.append(f"Coverage conflict on {m['code']}: {by[m['code']]['coverage']} against {m['coverage']}; kept partial.")
            by[m['code']]['coverage'] = 'partial'
    return list(by.values())


def merge_providers(dst, src, provider_notes, src_notes):
    for p, lv in (src or {}).items():
        if p not in dst or LEVELS[lv] > LEVELS[dst[p]]:
            dst[p] = lv
    for p, n in (src_notes or {}).items():
        provider_notes.setdefault(p, n)


# ---------------------------------------------------------------- collect raw checks
raw = {}
for pname, d in parts.items():
    for c in d['checks']:
        c = copy.deepcopy(c)
        c['_part'] = pname
        raw[c['key']] = c

# ---------------------------------------------------------------- build proposed set
proposed = {}
alias_payload = collections.defaultdict(list)  # canonical -> alias entries
for k, c in raw.items():
    if k in ALIASES:
        alias_payload[ALIASES[k]].append(c)
    else:
        proposed[k] = c

for canon, items in alias_payload.items():
    if canon in existing:
        continue  # handled as an extension below
    c = proposed[canon]
    notes = [c.get('notes')] if c.get('notes') else []
    c.setdefault('providers', {})
    c.setdefault('provider_notes', {})
    for a in items:
        c['controls'] = merge_controls(c['controls'], a['controls'], notes)
        merge_providers(c['providers'], a.get('providers'), c['provider_notes'], a.get('provider_notes'))
        for f in ('artifacts', 'evidence_kinds', 'sources', 'observation_types'):
            c[f] = dedupe((c.get(f) or []) + (a.get(f) or []))
        notes.append(f"Merged alias {a['key']}: {ALIAS_WHY[a['key']]}")
    c['notes'] = ' '.join(n for n in notes if n)
    c['aliases'] = [a['key'] for a in items]

for k, patch in CANON_PATCH.items():
    if k in proposed:
        proposed[k].update(patch)

# normalise every proposed check
for k, c in proposed.items():
    c['capabilities'] = dedupe(CAP_CANON.get(x, x) for x in c['capabilities'])
    if not c.get('aliases'):
        c['aliases'] = []
    c['aliases'] = [a for a in c['aliases'] if ALIASES.get(a) == k]  # only real merged aliases
    obs = []
    for o in (c.get('observation_types') or []):
        o = re.sub(r'\s*\(.*$', '', o).strip()
        obs.append(o)
    c['observation_types'] = dedupe(obs + OBS_FILL.get(k, [])) if obs else OBS_FILL.get(k, [])
    c['status'] = 'proposed'
    c['providers'] = c.get('providers') or {}
    c['implementations'] = [p for p, lv in c['providers'].items() if lv in ('supported', 'partial')]
    c['artifacts'] = c.get('artifacts') or []
    c['related'] = []

# phase 3 rows for checks defined by other researchers, and existing implementations
ext = collections.defaultdict(lambda: {'add_implementations': {}, 'notes': {}, 'sources': set()})
for pname, d in parts.items():
    for e in d.get('existing_implementations', []):
        key = ALIASES.get(e['check'], e['check'])
        lv = e.get('support')
        if lv not in LEVELS:
            continue
        if key in proposed:
            merge_providers(proposed[key]['providers'], {e['provider']: lv}, proposed[key].setdefault('provider_notes', {}), {e['provider']: e.get('note')} if e.get('note') else {})
            proposed[key]['sources'] = dedupe(proposed[key]['sources'] + [e.get('source', '').split(' ')[0]])
            proposed[key]['implementations'] = [p for p, l in proposed[key]['providers'].items() if l in ('supported', 'partial')]
        elif key in existing:
            x = ext[key]
            cur = x['add_implementations'].get(e['provider'])
            if cur is None or LEVELS[lv] > LEVELS[cur]:
                x['add_implementations'][e['provider']] = lv
            if e.get('note'):
                x['notes'].setdefault(e['provider'], e['note'])
            if e.get('source'):
                x['sources'].add(e['source'])
        else:
            print('UNKNOWN existing_implementation', e['check'], pname)

for k, rel, why in RELATED:
    for r in rel:
        if k in proposed:
            proposed[k]['related'].append({'key': r, 'why': why})
        if r in proposed:
            proposed[r]['related'].append({'key': k, 'why': why})

# extensions of existing checks from aliases
for canon, items in alias_payload.items():
    if canon not in existing:
        continue
    x = ext[canon]
    x['aliases'] = [a['key'] for a in items]
    x['add_capabilities'] = dedupe(CAP_CANON.get(cp, cp) for a in items for cp in a['capabilities'] if cp not in existing[canon]['capabilities'])
    x['capability_match'] = 'each'
    x['add_controls'] = []
    have = {m['code'] for m in existing[canon]['controls']}
    for a in items:
        for m in a['controls']:
            if m['code'] not in have and m['code'] not in {y['code'] for y in x['add_controls']}:
                x['add_controls'].append(dict(m, from_alias=a['key']))
        for p, lv in (a.get('providers') or {}).items():
            cur = x['add_implementations'].get(p)
            if cur is None or LEVELS[lv] > LEVELS[cur]:
                x['add_implementations'][p] = lv
        x['sources'].update(a.get('sources') or [])
    x['add_artifacts'] = dedupe(art for a in items for art in a.get('artifacts', []))
    x['alias_notes'] = {a['key']: ALIAS_WHY[a['key']] for a in items}

# existing check changes (parts + controls.json)
changes = []
for pname, d in parts.items():
    for ch in d.get('existing_check_changes', []):
        ch = dict(ch)
        ch['check'] = ALIASES.get(ch.get('check'), ch.get('check'))
        ch['_part'] = pname
        changes.append(ch)
ctl_files = {f: J(DOCS + 'coverage/' + f + '.controls.json') for f in ['gov-cs-hr', 'iam-ep-pe-ns-dm', 'sd-lm-bc']}
for f, lst in ctl_files.items():
    for e in lst:
        for ch in e.get('check_mapping_changes', []):
            n = {'check': ALIASES.get(ch['check'], ch['check']), 'source': f'coverage/{f}.controls.json {e["control"]}', '_part': f + '.controls'}
            if 'to_control' in ch:
                n.update(change='move_to_successor', control=ch['from_control'], to_control=ch['to_control'], rationale=ch.get('why'))
            else:
                n.update(change=('add_control' if ch.get('change') == 'add' else ch.get('change')), control=ch.get('control'), coverage=ch.get('coverage'), rationale=ch.get('rationale'))
            changes.append(n)
seen = set()
ext_changes = collections.defaultdict(list)
for ch in changes:
    k = ch['check']
    sig = (k, ch.get('change'), ch.get('control'), ch.get('to_control'))
    if sig in seen:
        continue
    seen.add(sig)
    target = ext_changes if k in existing else None
    if k in existing:
        ext_changes[k].append({f: ch.get(f) for f in ('change', 'control', 'to_control', 'coverage', 'rationale', 'source') if ch.get(f)})
    elif k in proposed:
        proposed[k].setdefault('_extra_changes', []).append(ch)
for k, lst in ext_changes.items():
    ext[k]['changes'] = lst

# downgrades
downgrades, dseen = [], {}
for pname, d in parts.items():
    for g in d.get('downgrades', []):
        sig = (g.get('check'), g.get('control'), g.get('requirement'))
        if sig in dseen:
            dseen[sig]['sources'].append(g.get('source'))
            continue
        g = dict(g, sources=[g.get('source')])
        dseen[sig] = g
        downgrades.append(g)
for k in list(ext):
    for g in downgrades:
        if g.get('check') == k and g.get('to') == 'partial':
            ext[k].setdefault('changes', []).append({'change': 'coverage_full_to_partial', 'control': g['control'], 'rationale': g.get('reason'), 'source': '; '.join(dedupe(s for s in g['sources'] if s))})
for g in downgrades:
    if g.get('check') and g['check'] not in ext:
        ext[g['check']]['changes'] = [{'change': 'coverage_full_to_partial', 'control': g['control'], 'rationale': g.get('reason'), 'source': '; '.join(dedupe(s for s in g['sources'] if s))}]

# proposed artifacts (dedupe log retention)
art_prop = {}
ART_ALIAS = {'log-retention-settings': 'log-store-retention-and-access-settings'}
for pname, d in parts.items():
    for a in d.get('artifacts_proposed', []):
        key = ART_ALIAS.get(a['key'], a['key'])
        if key in art_prop:
            art_prop[key]['sources_docs'].append(a.get('source'))
            art_prop[key].setdefault('aliases', []).append(a['key']) if a['key'] != key else None
            continue
        art_prop[key] = {'key': key, 'control': a.get('control'), 'objectives': a.get('objectives'), 'sources': a.get('sources'), 'why': a.get('why'), 'sources_docs': [a.get('source')]}
        if a['key'] != key:
            art_prop[key]['aliases'] = [a['key']]
for c in proposed.values():
    c['artifacts'] = dedupe(ART_ALIAS.get(a, a) for a in c['artifacts'])
for x in ext.values():
    if 'add_artifacts' in x:
        x['add_artifacts'] = dedupe(ART_ALIAS.get(a, a) for a in x['add_artifacts'])

# ---------------------------------------------------------------- order fields and write checks-proposed.json
ORDER = ['key', 'name', 'description', 'capabilities', 'capability_match', 'requires', 'implementations', 'resource_type',
         'frequency', 'remediation', 'controls', 'evidence_kinds', 'status', 'observation_types', 'providers', 'provider_notes',
         'artifacts', 'aliases', 'related', 'parameters', 'population', 'predicate', 'period', 'empty_population', 'outcomes',
         'module_gap', 'sources', 'notes']
out_checks = []
prefix_order = ['idp', 'vault', 'people', 'hr', 'devices', 'endpoint', 'cloud', 'assets', 'vcs', 'ci', 'tickets', 'alerts', 'observability', 'edge', 'scanner', 'apps', 'ai', 'verity']
for k in sorted(proposed, key=lambda k: (prefix_order.index(k.split('.')[0]), k)):
    c = proposed[k]
    c['sources'] = dedupe(s for s in c.get('sources', []) if s)
    o = {f: c[f] for f in ORDER if f in c and c[f] not in (None, '', [], {})}
    for f in ('aliases', 'related', 'artifacts', 'implementations', 'observation_types'):
        o.setdefault(f, c.get(f) or [])
    o['status'] = 'proposed'
    out_checks.append({f: o[f] for f in ORDER if f in o})

ext_out = []
for k in sorted(ext):
    x = ext[k]
    e = {'key': k, 'name': existing[k]['name'], 'today_implementations': existing[k]['implementations']}
    if x.get('aliases'):
        e['aliases'] = x['aliases']
        e['add_capabilities'] = x['add_capabilities']
        e['capability_match'] = x['capability_match']
        e['alias_notes'] = x['alias_notes']
    ai = {p: lv for p, lv in x['add_implementations'].items() if lv != 'not_possible' and p not in existing[k]['implementations']}
    np_ = sorted(p for p, lv in x['add_implementations'].items() if lv == 'not_possible')
    if ai:
        e['add_implementations'] = dict(sorted(ai.items()))
    if np_:
        e['not_possible'] = np_
    if x['notes']:
        e['provider_notes'] = x['notes']
    if x.get('add_controls'):
        e['add_controls'] = x['add_controls']
    if x.get('add_artifacts'):
        e['add_artifacts'] = x['add_artifacts']
    if x.get('changes'):
        e['changes'] = x['changes']
    e['sources'] = sorted(s for s in x['sources'] if s)
    ext_out.append(e)

# capability gaps: providers implementing a check outside its capabilities
pcap = collections.defaultdict(set)
for cp in caps:
    for p in cp['providers']:
        pcap[p['key']].add(cp['key'])
for pname, d in parts.items():
    for p in d.get('providers_proposed', []):
        for cpk in re.split(r',\s*', p.get('capability') or ''):
            pcap[p['key']].add(CAP_CANON.get(cpk, cpk))
    for cp in d.get('capabilities_proposed', []):
        for p in cp.get('providers') or []:
            pcap[p].add(CAP_CANON.get(cp['key'], cp['key']))
gaps = []
for e in ext_out:
    have = set(existing[e['key']]['capabilities']) | set(e.get('add_capabilities', []))
    for p in e.get('add_implementations', {}):
        if not pcap[p] & have:
            gaps.append((e['key'], p, sorted(pcap[p])))
for c in out_checks:
    have = set(c['capabilities']) | set(c.get('requires', []))
    for p in c['implementations']:
        if p != 'verity' and not pcap[p] & have:
            gaps.append((c['key'], p, sorted(pcap[p])))
json.dump(gaps, open(HERE + '/capability_gaps.json', 'w'), indent=0)
print('capability gaps', len(gaps))
for g in gaps: print('  GAP', g)
# resolve gaps: verity checks are fed by scanners, not implemented by them; other gaps add the capability
for k, p, pc in gaps:
    e = next((x for x in ext_out if x['key'] == k), None)
    if e is None:
        continue
    if k.startswith('verity.'):
        e.setdefault('fed_by', []).append(p)
        e['add_implementations'].pop(p, None)
        if not e['add_implementations']:
            e.pop('add_implementations')
    else:
        add = [c for c in pc if c != 'asset_discovery'][:1]
        e['add_capabilities'] = dedupe(e.get('add_capabilities', []) + add)
        e['capability_match'] = 'each'
        e.setdefault('capability_notes', []).append(f'{p} implements it from {add[0]}; add {add[0]} to the capabilities with capability_match each.')

# providers -> checks
prov = collections.defaultdict(lambda: {'existing': {}, 'proposed': {}})
for e in ext_out:
    for p, lv in e.get('add_implementations', {}).items():
        if p in existing[e['key']]['implementations']:
            continue
        prov[p]['existing'][e['key']] = lv
for c in out_checks:
    for p, lv in c['providers'].items():
        if lv != 'not_possible':
            prov[p]['proposed'][c['key']] = lv
provider_additions = {p: {'existing': dict(sorted(v['existing'].items())), 'proposed': dict(sorted(v['proposed'].items()))} for p, v in sorted(prov.items())}

obs_new = sorted({o for c in out_checks for o in c['observation_types'] if o not in OBS_BASE})
alias_count = len(ALIASES)
doc = {
    'about': 'Every new check proposed by the evidence connectors research, deduplicated. Proposal only: nothing here is in seed content. Shape follows seed/content/automation/checks.json plus the fields listed in fields.',
    'generated': '2026-11-23',
    'counts': {'proposed_checks': len(out_checks), 'aliases_merged': alias_count, 'raw_keys_before_dedup': len(raw),
               'existing_checks_extended': len(ext_out), 'providers_listed': len(provider_additions), 'proposed_artifacts': len(art_prop)},
    'fields': {
        'status': 'always proposed',
        'capability_match': 'absent means all listed capabilities must be connected, as in checks.json today. each means every connected provider of a listed capability is evaluated on its own and the check passes only when all of them pass; requires lists capabilities that must also be connected for the comparison. Needs an engine change (see 05-check-registry.md).',
        'observation_types': 'from 01-evidence-model.md 1.4, plus new types listed in observation_types_added',
        'providers': 'provider key to supported, partial or not_possible, from the feasibility tables',
        'artifacts': 'artifact keys from artifacts.json, or from artifacts_proposed below',
        'aliases': 'keys other researchers used for the same predicate; they are not to be created',
        'related': 'keys with a similar aim that stay separate, with the reason',
        'sources': 'research documents, relative to docs/product/evidence-connectors/',
    },
    'observation_types_added': obs_new,
    'alias_index': {a: c for a, c in sorted(ALIASES.items())},
    'checks': out_checks,
    'existing_check_extensions': ext_out,
    'provider_additions': provider_additions,
    'artifacts_proposed': sorted(art_prop.values(), key=lambda a: a['key']),
}
json.dump(doc, open(DOCS + 'checks-proposed.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- needs resolution
norm = lambda s: ' '.join(s.lower().split())
cov_files = {f: J(DOCS + 'coverage/' + f + '.json') for f in ['gov-cs-hr', 'iam-ep-pe-ns-dm', 'sd-lm-bc']}
entries = []
for f, lst in cov_files.items():
    for e in lst:
        for p in e['planned']:
            if p['kind'] != 'need':
                continue
            m = [x for x in NEEDS_MAP if x[0] == p['capability'] and norm(p['predicate']).startswith(norm(x[1]))]
            assert len(m) == 1, p
            cap, _, key, match, also, note = m[0]
            r = {'file': f'coverage/{f}.json', 'artifact': e['artifact'], 'control': e['control'], 'objectives': e['objectives'],
                 'capability': p['capability'], 'predicate': p['predicate'], 'fills': p.get('fills'), 'match': match}
            if key:
                r['check'] = key
                r['check_status'] = 'existing' if key in existing else 'proposed'
                if also:
                    r['also'] = also
                if note:
                    r['note'] = note
            else:
                reason, _, why = note.partition(': ')
                r['reason'] = reason
                r['why'] = why
            entries.append(r)
cnt = collections.Counter(r['match'] for r in entries)
uniq = {}
for r in entries:
    uniq.setdefault((r['capability'], r['predicate']), r)
ucnt = collections.Counter(r['match'] for r in uniq.values())
reasons = collections.Counter(r['reason'] for r in entries if r['match'] == 'unresolved')
by_cap = collections.defaultdict(collections.Counter)
for r in entries:
    by_cap[r['capability']][r['match']] += 1
needs_doc = {
    'about': 'Every NEED entry in coverage/*.json matched to a check key (existing in checks.json or proposed in checks-proposed.json), or marked unresolved with the reason. Generated 2026-11-23 by the reconciliation step.',
    'match_values': {'exact': 'the key tests this predicate', 'partial': 'the key tests part of it; note says what is left', 'unresolved': 'no key; reason not_defined (no researcher defined a check) or no_provider (no researched provider can collect it)'},
    'counts': {'entries': len(entries), 'unique_predicates': len(uniq), 'by_match': dict(cnt), 'unique_by_match': dict(ucnt),
               'unresolved_by_reason': dict(reasons), 'by_capability': {k: dict(v) for k, v in sorted(by_cap.items())},
               'resolved_to_existing': sum(1 for r in entries if r.get('check_status') == 'existing'),
               'resolved_to_proposed': sum(1 for r in entries if r.get('check_status') == 'proposed')},
    'needs': entries,
}
json.dump(needs_doc, open(DOCS + 'coverage/needs-resolution.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

# artifacts reached through resolved needs (primary key only)
pidx = {c['key']: c for c in doc['checks']}
eidx = {e['key']: e for e in doc['existing_check_extensions']}
for r in entries:
    k = r.get('check')
    if not k:
        continue
    if k in pidx:
        if r['artifact'] not in pidx[k]['artifacts']:
            pidx[k]['artifacts'].append(r['artifact'])
            pidx[k].setdefault('artifacts_from_needs', []).append(r['artifact'])
    elif k in existing:
        e = eidx.get(k)
        if e is None:
            e = {'key': k, 'name': existing[k]['name'], 'today_implementations': existing[k]['implementations'], 'sources': []}
            doc['existing_check_extensions'].append(e)
            eidx[k] = e
        if r['artifact'] not in e.get('add_artifacts', []) and not any(r['artifact'] == a['key'] and any(k in s.get('checks', []) for s in a['sources']) for a in [artifacts.get(r['artifact'], {'key': '', 'sources': []})]):
            e.setdefault('add_artifacts', []).append(r['artifact'])
doc['existing_check_extensions'].sort(key=lambda e: e['key'])
doc['counts']['existing_checks_extended'] = len(doc['existing_check_extensions'])
doc['fields']['artifacts_from_needs'] = 'artifacts that reach the check through a NEED resolved in coverage/needs-resolution.json'
json.dump(doc, open(DOCS + 'checks-proposed.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- scratch payload for markdown
other = {k: [] for k in ('decisions', 'defects', 'capabilities_proposed', 'providers_proposed')}
for pname, d in parts.items():
    for k in other:
        for x in d.get(k, []):
            x = dict(x, _part=pname)
            other[k].append(x)
json.dump({'downgrades': downgrades, **other, 'artifacts_proposed': list(art_prop.values()),
           'proposed_extra_changes': {k: c.get('_extra_changes') for k, c in proposed.items() if c.get('_extra_changes')}},
          open(HERE + '/merged.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(doc['counts'], needs_doc['counts']['by_match'], needs_doc['counts']['unique_by_match'], dict(reasons))
