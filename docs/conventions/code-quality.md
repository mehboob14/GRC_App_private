# Code quality and design principles

The architecture shape lives in [CLAUDE.md](../../CLAUDE.md), the backend layer rules in
[backend/CLAUDE.md](../../backend/CLAUDE.md), and the component rules in
[frontend/CLAUDE.md](../../frontend/CLAUDE.md). This file is the **cross-cutting quality bar** that
applies to every file in the repo. It is not optional polish: a change that works but violates these
is still a defect, because the next agent and the next engineer inherit it.

## SOLID, as it applies here

- **Single responsibility.** A router parses and delegates; a service holds one workflow; a
  repository runs queries; a React component renders. A function does one thing at one level of
  abstraction. If you need "and" to describe it, split it.
- **Open / closed.** Extend by adding, not by editing shared code. A new connector implements the
  connector interface; a new identity provider registers behind the seam; a new framework is
  content, not code. If adding a case means editing a `switch` in three files, the design is wrong —
  use a registry or a strategy.
- **Liskov.** An implementation honours its interface's full contract. A connector that raises
  instead of returning the `error` result state breaks every caller that trusted the interface —
  substitutability is the whole point of having the interface.
- **Interface segregation.** Service interfaces are narrow and caller-shaped. A module should not
  depend on methods it never calls. Prefer several small service methods over one god-method with a
  mode flag.
- **Dependency inversion.** Modules depend on service *interfaces*, never on another module's
  repository, models, or tables. The identity seam and the connector framework are dependency
  inversion in practice: the app depends on the abstraction, the provider plugs in.

## Reuse before you write

Before writing a component, hook, helper, or service method, look for it first:

- **Frontend:** `components/ui/` (primitives), the feature's own `components/` and `hooks/`, then `lib/`.
- **Backend:** the module's service, `shared/` (pure helpers), existing repository methods.

If something almost fits, extend or lift it — do not fork it. A second near-copy is a smell; a third
is a bug waiting to be fixed in only two of the three places.

## But do not over-abstract

Duplication is cheaper than the wrong abstraction. Extract on the **third real occurrence**, not the
first anticipated one. A shared helper that takes five flags to serve three callers is worse than
three honest functions. What a requirement calls "configurable" lives in a **table**, not in a
premature settings layer.

## Functions and files

- Small functions, one level of abstraction each. If you have to scroll to read it, split it.
- Names carry intent: `expiry_from_capture`, not `calc`; `PolicyApprovalDrawer`, not `Modal2`.
- No dead code, no commented-out blocks, no `TODO` without a tracked issue. Delete it — git remembers.
- Comments explain **why**, never **what**. Self-documenting code first; a comment earns its place by
  capturing a non-obvious reason or a sharp edge, not by narrating the line below it.

## State and purity

- Business calculations are **pure functions** wherever they can be: same input, same output, no
  hidden I/O. Pure logic is the trivially-testable part — keep it that way.
- Prefer immutable data. Mutating a shared structure to save an allocation is a false economy that
  costs a debugging session.
- Every observable state is handled: on the frontend, loading, empty, and error are **required**, not
  follow-ups; on the backend, `error` is distinct from `fail`.

## Consistency beats cleverness

Match the surrounding code. A module that reads like every other module is maintainable; a locally
clever one taxes everyone who touches it next. The reference shape for a backend module is in
[backend/CLAUDE.md](../../backend/CLAUDE.md); for a frontend feature, in
[frontend/CLAUDE.md](../../frontend/CLAUDE.md). Copy the established pattern, not a competing one.
