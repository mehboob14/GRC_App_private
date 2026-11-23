import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorBanner,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { engagementApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import type { ScopeItem, ScopeItemKind } from "@/lib/api/types";

/**
 * What is in scope: one list for the workspace, in or out decided for this framework only
 * (guided onboarding SC-0, decision D-6). The other frameworks' decisions show beside each item,
 * so a person sees where scopes differ. Out needs a reason, asked in a popup. A change that
 * matters to an auditor (inside a SOC 2 period, or a certified ISO scope) says so after saving.
 */

const KINDS: { value: ScopeItemKind; label: string }[] = [
  { value: "service", label: "Service" },
  { value: "legal_entity", label: "Legal entity" },
  { value: "site", label: "Site" },
  { value: "environment", label: "Environment" },
  { value: "system", label: "System" },
  { value: "vendor", label: "Vendor" },
  { value: "people_group", label: "People group" },
  { value: "data_type", label: "Data type" },
];
const KIND_LABEL = Object.fromEntries(KINDS.map((k) => [k.value, k.label])) as Record<ScopeItemKind, string>;
const FRAMEWORK_LABEL: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

type Pending = { kind: "out" | "retire"; item: ScopeItem } | null;

export function ScopeItemsSection({
  frameworkCode,
  hasEngagement,
  canManage,
}: {
  frameworkCode: string;
  hasEngagement: boolean;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = ["scope-items", frameworkCode];
  const items = useQuery({
    queryKey: key,
    queryFn: () => engagementApi.scopeItems(frameworkCode),
  });
  const [adding, setAdding] = useState(false);
  const [kind, setKind] = useState<ScopeItemKind>("system");
  const [name, setName] = useState("");
  const [pending, setPending] = useState<Pending>(null);
  const [reason, setReason] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const suggestions = useQuery({
    queryKey: ["scope-suggestions"],
    queryFn: engagementApi.scopeSuggestions,
    enabled: suggesting,
  });
  const acceptSuggestions = useMutation({
    mutationFn: () =>
      engagementApi.acceptScopeSuggestions(
        (suggestions.data ?? [])
          .filter((s) => picked.has(s.ref_id))
          .map((s) => ({ ref_type: s.ref_type, ref_id: s.ref_id })),
      ),
    onSuccess: (result) => {
      refresh();
      void queryClient.invalidateQueries({ queryKey: ["scope-suggestions"] });
      setSuggesting(false);
      setPicked(new Set());
      toast({ title: `${result.added} added. Decide for each framework below.`, tone: "success" });
    },
  });

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["scope-items"] });
  const tell = (notices: string[]) =>
    notices.forEach((notice) => toast({ title: notice, tone: "neutral", durationMs: 9000 }));

  const add = useMutation({
    mutationFn: () => engagementApi.addScopeItem({ kind, name: name.trim() }),
    onSuccess: () => {
      refresh();
      setAdding(false);
      setName("");
      toast({ title: "Item added", tone: "success" });
    },
  });
  const decide = useMutation({
    mutationFn: (args: { item: ScopeItem; in_scope: boolean; reason: string | null }) =>
      engagementApi.decideScopeItem(args.item.id, frameworkCode, {
        in_scope: args.in_scope,
        reason: args.reason,
      }),
    onSuccess: (result) => {
      refresh();
      setPending(null);
      setReason("");
      tell(result.notices);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "scope"), tone: "danger" }),
  });
  const retire = useMutation({
    mutationFn: (item: ScopeItem) => engagementApi.retireScopeItem(item.id, reason.trim()),
    onSuccess: (result) => {
      refresh();
      setPending(null);
      setReason("");
      toast({ title: "Item removed", tone: "success" });
      tell(result.notices);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "scope item"), tone: "danger" }),
  });

  const frameworkLabel = FRAMEWORK_LABEL[frameworkCode] ?? frameworkCode;
  const list = items.data ?? [];

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">What is in scope</h2>
        {canManage ? (
          <span className="flex gap-2">
            <Button variant="ghost" onClick={() => setSuggesting(true)}>
              Suggest from your records
            </Button>
            <Button variant="secondary" onClick={() => setAdding(true)}>
              Add item
            </Button>
          </span>
        ) : null}
      </div>

      {!hasEngagement ? (
        <p className="mt-3 text-body-sm text-text-secondary">Save the audit setup above, then decide what it covers.</p>
      ) : items.isLoading ? (
        <Skeleton className="mt-4 h-24 w-full" />
      ) : items.isError ? (
        <ErrorBanner className="mt-4" title="Couldn’t load the scope items">
          {describeError(items.error, "scope items").message}
        </ErrorBanner>
      ) : list.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title="Nothing listed yet"
            description="Add the services, systems, sites and teams an auditor will ask about. Every framework shares this list and decides for itself."
          />
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {list.map((item) => (
            <li key={item.id} className="flex flex-wrap items-start gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-body-md font-semibold text-text-primary">{item.name}</p>
                <p className="text-caption text-text-subtle">
                  {KIND_LABEL[item.kind]}
                  {item.others.map((o) => (
                    <span key={o.framework_code}>
                      {`. ${FRAMEWORK_LABEL[o.framework_code] ?? o.framework_code}: ${o.in_scope ? "in" : "out"}`}
                    </span>
                  ))}
                </p>
                {item.in_scope === false && item.reason ? (
                  <p className="mt-0.5 text-body-sm text-text-secondary">{item.reason}</p>
                ) : null}
              </div>
              {item.in_scope === null ? (
                <StatusPill status="pending" label="Not decided" />
              ) : item.in_scope ? (
                <StatusPill status="success" label={`In ${frameworkLabel}`} />
              ) : (
                <StatusPill status="neutral" label={`Out of ${frameworkLabel}`} />
              )}
              {canManage ? (
                <span className="flex gap-1">
                  {item.in_scope !== true ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => decide.mutate({ item, in_scope: true, reason: null })}
                    >
                      Include
                    </Button>
                  ) : null}
                  {item.in_scope !== false ? (
                    <Button variant="ghost" size="sm" onClick={() => setPending({ kind: "out", item })}>
                      Leave out
                    </Button>
                  ) : null}
                  <Button variant="ghost" size="sm" onClick={() => setPending({ kind: "retire", item })}>
                    Remove
                  </Button>
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <Dialog open={suggesting} onOpenChange={setSuggesting}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Suggested from your records</DialogTitle>
            <DialogDescription>Live assets and critical or high tier vendors not on the list yet.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            {suggestions.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (suggestions.data ?? []).length === 0 ? (
              <p className="text-body-sm text-text-secondary">Nothing to suggest. Every asset and key vendor is listed.</p>
            ) : (
              <ul className="max-h-80 space-y-2 overflow-y-auto">
                {(suggestions.data ?? []).map((s) => (
                  <li key={s.ref_id}>
                    <label className="flex items-center gap-2 text-body-md text-text-primary">
                      <Checkbox
                        checked={picked.has(s.ref_id)}
                        onCheckedChange={(v) =>
                          setPicked((current) => {
                            const next = new Set(current);
                            if (v === true) next.add(s.ref_id);
                            else next.delete(s.ref_id);
                            return next;
                          })
                        }
                      />
                      {s.name}
                      <span className="text-caption text-text-subtle">{KIND_LABEL[s.kind]}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setSuggesting(false)}>
              Cancel
            </Button>
            <Button disabled={picked.size === 0} loading={acceptSuggestions.isPending} onClick={() => acceptSuggestions.mutate()}>
              Add {picked.size || ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Add a scope item</DialogTitle>
            <DialogDescription>Every framework sees it and decides for itself.</DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-3">
            <SelectField label="Kind">
              <Select value={kind} onValueChange={(v) => setKind(v as ScopeItemKind)}>
                <SelectTrigger aria-label="Kind" />
                <SelectContent>
                  {KINDS.map((k) => (
                    <SelectItem key={k.value} value={k.value}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <TextField label="Name" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button disabled={!name.trim()} loading={add.isPending} onClick={() => add.mutate()}>
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPending(null);
            setReason("");
          }
        }}
      >
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>
              {pending?.kind === "retire" ? "Remove from every framework" : `Leave out of ${frameworkLabel}`}
            </DialogTitle>
            <DialogDescription>
              {pending?.kind === "retire"
                ? "The item stays in the history with your reason."
                : "Your auditor sees this reason."}
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <p className="mb-3 text-body-md font-semibold text-text-primary">{pending?.item.name}</p>
            <TextArea label="Reason" rows={3} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setPending(null)}>
              Cancel
            </Button>
            <Button
              disabled={!reason.trim()}
              loading={decide.isPending || retire.isPending}
              onClick={() => {
                if (!pending) return;
                if (pending.kind === "retire") retire.mutate(pending.item);
                else decide.mutate({ item: pending.item, in_scope: false, reason: reason.trim() });
              }}
            >
              {pending?.kind === "retire" ? "Remove" : "Leave out"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
