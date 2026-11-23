import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  RadioGroup,
  RadioGroupItem,
  SearchableSelect,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { apiFetch } from "@/lib/api/client";
import { engagementApi } from "@/lib/api/endpoints";
import { errorToast } from "@/lib/api/describe-error";
import type { AuditType, CommitmentSource, Engagement } from "@/lib/api/types";

/**
 * The programme around one audit (guided onboarding phase 3): its dated plan and cycles, what
 * the company promises customers, the vendors that count, and scope changes inside a SOC 2
 * period. Each card is one focused job; decisions that need a reason ask for it in a popup.
 */

const FRAMEWORK_LABEL: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

function day(value: string | null): string {
  if (!value) return "No date";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function Card({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">{title}</h2>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

// -- plan and cycles --------------------------------------------------------------------------

const NEXT_TYPES: Record<string, { value: AuditType; label: string }[]> = {
  categories: [{ value: "type_1", label: "Type 1 (set Type 2 dates after it opens)" }],
  applicability: [
    { value: "surveillance", label: "Surveillance audit" },
    { value: "recertification", label: "Recertification" },
    { value: "initial_certification", label: "Initial certification" },
  ],
};

export function PlanCard({
  frameworkCode,
  scopeModel,
  engagement,
  canManage,
}: {
  frameworkCode: string;
  scopeModel: "categories" | "applicability";
  engagement: Engagement;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const plan = useQuery({
    queryKey: ["milestones", frameworkCode, engagement.id, engagement.audit_type],
    queryFn: () => engagementApi.milestones(frameworkCode),
  });
  const cycles = useQuery({
    queryKey: ["cycles", frameworkCode],
    queryFn: () => engagementApi.cycles(frameworkCode),
  });
  const [draft, setDraft] = useState<Record<string, { planned_on: string; actual_on: string }>>({});
  const [nextOpen, setNextOpen] = useState(false);
  const [nextName, setNextName] = useState("");
  const [nextType, setNextType] = useState<AuditType>(NEXT_TYPES[scopeModel]?.[0]?.value ?? "type_1");

  useEffect(() => {
    const seed: Record<string, { planned_on: string; actual_on: string }> = {};
    for (const m of plan.data ?? []) {
      seed[m.kind] = { planned_on: m.planned_on ?? "", actual_on: m.actual_on ?? "" };
    }
    setDraft(seed);
  }, [plan.data]);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["milestones"] }),
      queryClient.invalidateQueries({ queryKey: ["cycles"] }),
      queryClient.invalidateQueries({ queryKey: ["engagement"] }),
      queryClient.invalidateQueries({ queryKey: ["onboarding-status"] }),
    ]);
  const save = useMutation({
    mutationFn: () =>
      engagementApi.saveMilestones(
        frameworkCode,
        (plan.data ?? [])
          .filter((m) => !m.from_engagement)
          .map((m) => ({
            kind: m.kind,
            planned_on: draft[m.kind]?.planned_on || null,
            actual_on: draft[m.kind]?.actual_on || null,
          })),
      ),
    onSuccess: async () => {
      await refresh();
      toast({ title: "Plan saved", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "plan"), tone: "danger" }),
  });
  const next = useMutation({
    mutationFn: () => engagementApi.nextCycle(frameworkCode, { name: nextName.trim(), audit_type: nextType }),
    onSuccess: async () => {
      await refresh();
      setNextOpen(false);
      toast({ title: "Next cycle started. The last one is kept in the history.", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "cycle"), tone: "danger" }),
  });

  const earlier = (cycles.data ?? []).filter((c) => !c.is_current);

  return (
    <Card
      title="Audit plan"
      action={
        canManage ? (
          <Button variant="ghost" onClick={() => setNextOpen(true)}>
            Start next cycle
          </Button>
        ) : null
      }
    >
      {plan.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid gap-x-4 gap-y-3">
          <div className="hidden grid-cols-[1fr_160px_160px] text-caption text-text-subtle sm:grid">
            <span>Milestone</span>
            <span>Planned</span>
            <span>Done on</span>
          </div>
          {(plan.data ?? []).map((m) => (
            <div key={m.kind} className="grid items-center gap-2 sm:grid-cols-[1fr_160px_160px]">
              <span className="text-body-md text-text-primary">{m.label}</span>
              {m.from_engagement ? (
                <span className="text-body-sm text-text-secondary sm:col-span-2">
                  {day(m.planned_on)}. Set in audit details.
                </span>
              ) : (
                <>
                  <input
                    type="date"
                    aria-label={`${m.label} planned`}
                    disabled={!canManage}
                    value={draft[m.kind]?.planned_on ?? ""}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, [m.kind]: { planned_on: e.target.value, actual_on: d[m.kind]?.actual_on ?? "" } }))
                    }
                    className="h-9 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary"
                  />
                  <input
                    type="date"
                    aria-label={`${m.label} done on`}
                    disabled={!canManage}
                    value={draft[m.kind]?.actual_on ?? ""}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, [m.kind]: { planned_on: d[m.kind]?.planned_on ?? "", actual_on: e.target.value } }))
                    }
                    className="h-9 rounded-sm border border-border bg-surface-primary px-2 text-body-sm text-text-primary"
                  />
                </>
              )}
            </div>
          ))}
        </div>
      )}
      {canManage ? (
        <div className="mt-5 flex items-center gap-3 border-t border-border pt-4">
          <Button variant="secondary" loading={save.isPending} onClick={() => save.mutate()}>
            Save plan
          </Button>
          <p className="text-body-sm text-text-subtle">Your auditor sets the real timeline.</p>
        </div>
      ) : null}
      {earlier.length ? (
        <div className="mt-5 border-t border-border pt-4">
          <p className="text-caption text-text-subtle">Earlier cycles</p>
          <ul className="mt-2 space-y-1">
            {earlier.map((c) => (
              <li key={c.id} className="text-body-sm text-text-secondary">
                {c.name}, closed. Started {day(c.created_at.slice(0, 10))}.
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Dialog open={nextOpen} onOpenChange={setNextOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Start the next cycle</DialogTitle>
            <DialogDescription>
              The current cycle closes and stays in the history. Scope decisions and vendors carry over.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <TextField label="Name" value={nextName} maxLength={200} onChange={(e) => setNextName(e.target.value)} />
            <RadioGroup value={nextType} onValueChange={(v) => setNextType(v as AuditType)}>
              {(NEXT_TYPES[scopeModel] ?? []).map((t) => (
                <RadioGroupItem key={t.value} value={t.value} label={t.label} />
              ))}
            </RadioGroup>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setNextOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!nextName.trim()} loading={next.isPending} onClick={() => next.mutate()}>
              Start
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// -- commitments ----------------------------------------------------------------------------

const SOURCES: { value: CommitmentSource; label: string }[] = [
  { value: "contract", label: "Contract" },
  { value: "service_levels", label: "Service levels" },
  { value: "privacy_notice", label: "Privacy notice" },
  { value: "website", label: "Website" },
  { value: "other", label: "Somewhere else" },
];

export function CommitmentsCard({ canManage }: { canManage: boolean }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const list = useQuery({ queryKey: ["commitments"], queryFn: engagementApi.commitments });
  const [open, setOpen] = useState(false);
  const [statement, setStatement] = useState("");
  const [source, setSource] = useState<CommitmentSource>("contract");
  const [ref, setRef] = useState("");
  const [retiring, setRetiring] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["commitments"] });
  const add = useMutation({
    mutationFn: () =>
      engagementApi.addCommitment({
        statement: statement.trim(),
        source_kind: source,
        source_ref: ref.trim() || null,
        points_at: [],
      }),
    onSuccess: () => {
      refresh();
      setOpen(false);
      setStatement("");
      setRef("");
      toast({ title: "Promise added", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "promise"), tone: "danger" }),
  });
  const retire = useMutation({
    mutationFn: (id: string) => engagementApi.retireCommitment(id, reason.trim()),
    onSuccess: () => {
      refresh();
      setRetiring(null);
      setReason("");
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "promise"), tone: "danger" }),
  });
  const sourceLabel = Object.fromEntries(SOURCES.map((s) => [s.value, s.label]));

  return (
    <Card
      title="What you promise customers"
      action={
        canManage ? (
          <Button variant="secondary" onClick={() => setOpen(true)}>
            Add a promise
          </Button>
        ) : null
      }
    >
      {list.isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : (list.data ?? []).length === 0 ? (
        <p className="text-body-sm text-text-secondary">
          Uptime, security terms, privacy promises. They decide your SOC 2 categories and feed the ISO
          context register.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {(list.data ?? []).map((c) => (
            <li key={c.id} className="flex items-start gap-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="text-body-md text-text-primary">{c.statement}</p>
                <p className="text-caption text-text-subtle">
                  {sourceLabel[c.source_kind]}
                  {c.source_ref ? `. ${c.source_ref}` : ""}
                </p>
              </div>
              {canManage ? (
                <Button variant="ghost" size="sm" onClick={() => setRetiring(c.id)}>
                  Remove
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Add a promise</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <TextArea label="What you promise" rows={2} maxLength={1000} value={statement} onChange={(e) => setStatement(e.target.value)} />
            <SelectField label="Where it is written">
              <Select value={source} onValueChange={(v) => setSource(v as CommitmentSource)}>
                <SelectTrigger aria-label="Where it is written" />
                <SelectContent>
                  {SOURCES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextField label="Section or link" optional value={ref} maxLength={300} onChange={(e) => setRef(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!statement.trim()} loading={add.isPending} onClick={() => add.mutate()}>
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={retiring !== null} onOpenChange={(o) => (o ? null : setRetiring(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Remove this promise</DialogTitle>
            <DialogDescription>It stays in the history with your reason.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <TextArea label="Reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setRetiring(null)}>
              Cancel
            </Button>
            <Button disabled={!reason.trim()} loading={retire.isPending} onClick={() => retiring && retire.mutate(retiring)}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// -- vendors that count ----------------------------------------------------------------------

type VendorRow = { id: string; name: string };

export function VendorsCard({
  frameworkCode,
  scopeModel,
  hasEngagement,
  canManage,
}: {
  frameworkCode: string;
  scopeModel: "categories" | "applicability";
  hasEngagement: boolean;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const soc2 = scopeModel === "categories";
  const list = useQuery({
    queryKey: ["engagement-vendors", frameworkCode],
    queryFn: () => engagementApi.vendors(frameworkCode),
    enabled: hasEngagement,
  });
  const [open, setOpen] = useState(false);
  const [vendorId, setVendorId] = useState<string | null>(null);
  const [method, setMethod] = useState<"carve_out" | "included">("carve_out");
  const [removing, setRemoving] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const all = useQuery({
    queryKey: ["vendor-options"],
    queryFn: () => apiFetch<{ items: VendorRow[] }>("/vendors?page_size=200"),
    enabled: open,
  });
  const options = useMemo(
    () => (all.data?.items ?? []).map((v) => ({ value: v.id, label: v.name })),
    [all.data],
  );
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["engagement-vendors"] });
  const add = useMutation({
    mutationFn: () =>
      engagementApi.setVendor(frameworkCode, vendorId ?? "", {
        role: soc2 ? "subservice" : "supplier",
        method: soc2 ? method : null,
        note: null,
      }),
    onSuccess: () => {
      refresh();
      setOpen(false);
      setVendorId(null);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "vendor"), tone: "danger" }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => engagementApi.removeVendor(frameworkCode, id, reason.trim()),
    onSuccess: () => {
      refresh();
      setRemoving(null);
      setReason("");
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "vendor"), tone: "danger" }),
  });
  const label = FRAMEWORK_LABEL[frameworkCode] ?? frameworkCode;

  return (
    <Card
      title={soc2 ? "Subservice organisations" : "Suppliers the scope depends on"}
      action={
        canManage && hasEngagement ? (
          <Button variant="secondary" onClick={() => setOpen(true)}>
            Add vendor
          </Button>
        ) : null
      }
    >
      {!hasEngagement ? (
        <p className="text-body-sm text-text-secondary">Save the audit setup above first.</p>
      ) : (list.data ?? []).length === 0 ? (
        <p className="text-body-sm text-text-secondary">
          {soc2
            ? "Vendors whose controls your SOC 2 report relies on, such as your cloud host. Your description names each one and whether it is carved out or included."
            : `Suppliers your ${label} scope depends on.`}
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {(list.data ?? []).map((v) => (
            <li key={v.vendor_id} className="flex items-center gap-3 py-2.5">
              <span className="flex-1 text-body-md text-text-primary">{v.name}</span>
              {v.method ? (
                <span className="text-body-sm text-text-secondary">
                  {v.method === "carve_out" ? "Carved out" : "Included"}
                </span>
              ) : null}
              {canManage ? (
                <Button variant="ghost" size="sm" onClick={() => setRemoving(v.vendor_id)}>
                  Remove
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>{soc2 ? "Add a subservice organisation" : "Add a supplier"}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <SearchableSelect
              options={options}
              value={vendorId}
              onChange={setVendorId}
              placeholder="Choose a vendor"
              searchPlaceholder="Search vendors"
              aria-label="Vendor"
            />
            {soc2 ? (
              <RadioGroup value={method} onValueChange={(v) => setMethod(v as "carve_out" | "included")}>
                <RadioGroupItem value="carve_out" label="Carved out" description="Described, with the controls you expect of them. The usual choice." />
                <RadioGroupItem value="included" label="Included" description="Their controls are examined as part of your report." />
              </RadioGroup>
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!vendorId} loading={add.isPending} onClick={() => add.mutate()}>
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={removing !== null} onOpenChange={(o) => (o ? null : setRemoving(null))}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Remove from this audit</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <TextArea label="Reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setRemoving(null)}>
              Cancel
            </Button>
            <Button disabled={!reason.trim()} loading={remove.isPending} onClick={() => removing && remove.mutate(removing)}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// -- changes in the period ----------------------------------------------------------------------

export function ChangesCard({ frameworkCode }: { frameworkCode: string }) {
  const changes = useQuery({
    queryKey: ["period-changes", frameworkCode],
    queryFn: () => engagementApi.changes(frameworkCode),
  });
  if (!changes.data || changes.data.length === 0) return null;
  return (
    <Card title="Changes in the observation period">
      <ul className="space-y-1.5">
        {changes.data.map((c, i) => (
          <li key={`${c.occurred_at}-${i}`} className="text-body-sm text-text-secondary">
            <span className="tabular text-text-subtle">{day(c.occurred_at.slice(0, 10))}</span> {c.summary}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-caption text-text-subtle">Your system description has to disclose these.</p>
    </Card>
  );
}
