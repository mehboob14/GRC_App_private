"""Task & Issue Management — the operational work register.

One entity (``task_kind`` discriminates task vs issue), a single ``status`` with
its transitions in the service, a columnar append-only ``task_transitions``
history, SLA clocks derived on read, recurrence, templates, and links to controls
and evidence through the polymorphic ``links`` table.

Schema and permissions land in ``20260824_1200_tasks_module.py``; the service and
API fill the contract the frontend was built against.
"""
