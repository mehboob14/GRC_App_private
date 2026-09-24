import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Icon,
  Skeleton,
  StatusPill,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TextField,
  TR,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { listDiscoveredApps, recordDiscoveredApp, triageDiscoveredApp } from "../api";
import type { DiscoveredApp } from "../types";
import { fmtDate } from "../tokens";
import { Panel } from "./panel";

const DISPOSITION_META: Record<
  string,
  { label: string; family: "warning" | "success" | "progress" | "neutral" }
> = {
  pending: { label: "Undecided", family: "warning" },
  added_as_vendor: { label: "Sent to intake", family: "progress" },
  linked_to_vendor: { label: "Already ours", family: "success" },
  ignored: { label: "Ignored", family: "neutral" },
};

/**
 * Apps in use that never came through intake.
 *
 * Entered by hand today. An identity provider fills the same table when one is
 * connected, which is why every row carries where it came from: a name somebody
 * typed and a name a connector found are different kinds of claim.
 */
export function ShadowItPanel({ canManage }: { canManage: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["vendor-discovered-apps"], queryFn: listDiscoveredApps });
  const [name, setName] = useState("");
  const [users, setUsers] = useState("");

  const apply = (items: DiscoveredApp[]) =>
    queryClient.setQueryData(["vendor-discovered-apps"], items);

  const record = useMutation({
    mutationFn: () =>
      recordDiscoveredApp({
        app_name: name.trim(),
        authorizing_users: users ? Number(users) : 0,
      }),
    onSuccess: (items) => {
      apply(items);
      setName("");
      setUsers("");
      toast({ title: "App recorded", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "app"), tone: "danger" }),
  });

  const triage = useMutation({
    mutationFn: (input: { id: string; disposition: string }) =>
      triageDiscoveredApp(input.id, input.disposition),
    onSuccess: (items, input) => {
      apply(items);
      if (input.disposition === "added_as_vendor") {
        void queryClient.invalidateQueries({ queryKey: ["vendor-intake"] });
      }
      toast({
        title:
          input.disposition === "added_as_vendor"
            ? "Raised as an intake request"
            : "App triaged",
        tone: "success",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "app"), tone: "danger" }),
  });

  const apps = query.data ?? [];
  const undecided = apps.filter((a) => a.disposition === "pending");

  return (
    <Panel
      title="Shadow IT"
      count={apps.length || undefined}
      description={undecided.length > 0 ? `${undecided.length} undecided` : undefined}
    >
      {query.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : apps.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          Nothing recorded. Add an app you have found in use, or connect an identity provider to
          fill this automatically.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <Table density="compact">
            <THead>
              <TR>
                <TH>App</TH>
                <TH numeric>People</TH>
                <TH>First seen</TH>
                <TH>Status</TH>
                {canManage ? <TH aria-label="Actions" /> : null}
              </TR>
            </THead>
            <TBody>
              {apps.map((a) => {
                const status = DISPOSITION_META[a.disposition] ?? {
                  label: a.disposition,
                  family: "neutral" as const,
                };
                return (
                  <TR key={a.id}>
                    <TD>
                      <span className="text-body-md text-text-primary">{a.app_name}</span>
                      {a.source !== "manual" ? (
                        <Badge variant="neutral">{a.source}</Badge>
                      ) : null}
                      {a.oauth_scopes.length > 0 ? (
                        <p className="text-caption text-text-subtle">
                          {a.oauth_scopes.join(", ")}
                        </p>
                      ) : null}
                    </TD>
                    <TD numeric>
                      <span className="tabular text-body-sm text-text-secondary">
                        {a.authorizing_users}
                      </span>
                    </TD>
                    <TD>
                      <span className="text-body-sm text-text-secondary">
                        {fmtDate(a.first_seen_at)}
                      </span>
                    </TD>
                    <TD>
                      <StatusPill status={status.family} label={status.label} kind="inline" />
                      {a.vendor_id ? (
                        <Link
                          to={`/vendors/${a.vendor_id}`}
                          className="ml-2 text-caption text-text-link underline-offset-2 hover:underline"
                        >
                          Open vendor
                        </Link>
                      ) : null}
                    </TD>
                    {canManage ? (
                      <TD>
                        {a.disposition === "pending" ? (
                          <span className="flex flex-wrap gap-1.5">
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={triage.isPending && triage.variables?.id === a.id}
                              onClick={() =>
                                triage.mutate({ id: a.id, disposition: "added_as_vendor" })
                              }
                            >
                              Send to intake
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => triage.mutate({ id: a.id, disposition: "ignored" })}
                            >
                              Ignore
                            </Button>
                          </span>
                        ) : null}
                      </TD>
                    ) : null}
                  </TR>
                );
              })}
            </TBody>
          </Table>
        </div>
      )}

      {canManage ? (
        <form
          className="mt-3 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) record.mutate();
          }}
        >
          <div className="w-56">
            <TextField
              label="App in use"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Figma"
            />
          </div>
          <div className="w-32">
            <TextField
              label="People"
              optional
              type="number"
              min={0}
              value={users}
              onChange={(e) => setUsers(e.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary" loading={record.isPending} disabled={!name.trim()}>
            <Icon name="plus" className="size-4" />
            Record
          </Button>
        </form>
      ) : null}
    </Panel>
  );
}
