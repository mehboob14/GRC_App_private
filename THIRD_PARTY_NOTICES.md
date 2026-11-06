# Third party notices

Verity ships content that builds on open source work. This file carries the notices those licences
ask for.

## Probo

The control library (the shipped controls and their guidance, task A6 of the control framework
change) was derived from the Probo control library, and the ISO 27001 requirement identifiers come
from Probo's framework catalogue. Probo is MIT licensed: https://github.com/getprobo/probo

Probo's licence covers Probo's own work. It does not extend to the text of the standards its
catalogues refer to, and Verity does not ship that text: requirement wording in the packs is
Verity's, and the mappings are Verity's own.

```
MIT License

Copyright (c) 2025 Probo Inc <hello@probo.com>.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## Open Lane policy hub

The policy templates in `backend/src/verity/seed/content/policies` come from the Open Lane policy
hub, Apache License 2.0: https://github.com/theopenlane/policy-hub (commit
`22ace724638b897062714bcf447b84be531ba03a`). The policy text is unaltered; the platform adds a summary,
placeholders and the list of requirements each policy speaks to. Each template records its source,
commit and licence.
