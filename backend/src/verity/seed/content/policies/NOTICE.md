# Third-party content: policy templates

The policy templates in `document_templates.json` are derived from the
**Openlane Policy Hub**.

| | |
|---|---|
| Source | https://github.com/theopenlane/policy-hub |
| Commit | `22ace724638b897062714bcf447b84be531ba03a` (2026-01-28) |
| Licence | Apache License 2.0 |
| Retrieved | 2026-09-05 |

Apache 2.0 permits commercial use and redistribution. It requires that we carry
the licence, give attribution, and state what we changed. All three are met:

- **Licence** — a copy is at `LICENSE-openlane-policy-hub.txt` beside this file.
- **Attribution** — every row carries `source`, `source_url`, `source_commit`
  and `license`, and the template picker shows the source and licence to the
  user before they adopt a policy.
- **Changes** — stated below.

## What was changed

1. **Markdown converted to HTML.** `scripts/build_policy_templates.py` renders
   each file with Python-Markdown (tables, sane lists, attr_list, md_in_html).
   The policy wording itself is unaltered.
2. **Frontmatter lifted into columns.** `title`, `satisfies` and `tags` moved
   from YAML frontmatter into `document_templates` columns so the platform can
   search by SOC 2 criterion and topic.
3. **Placeholders catalogued.** The `{{field}}` tokens already present upstream
   are counted at build time and stored alongside the content, so the editor can
   show what a customer still has to decide. The tokens themselves are unchanged.

Nothing else is edited. When a tenant starts a document from a template they get
their own copy, and any wording they change from that point is theirs alone.

## Updating

Re-run against a fresh clone, then review the diff like any other content change:

```
uv run --with markdown python scripts/build_policy_templates.py --source <clone>
```

`markdown` is a build-time tool only and is deliberately not a project
dependency — nothing converts markdown at runtime.

## Templates written by Verity

Fourteen templates in `document_templates.json` are not from the Openlane Policy Hub. They carry
`"source": "verity"` and were written for Verity (2026-10-16): the ISMS scope statement, the context
and interested parties register, security objectives, the risk assessment method, change
management, document control, internal audit, management review, corrective action, acceptable use,
remote working, competence and awareness, the security communication plan and cloud services
security. They refer to ISO/IEC 27001, PCI DSS and SOC 2 requirements by identifier only and
reproduce no text of those standards. The template picker shows them as written by Verity.
