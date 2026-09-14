import { useEffect, useMemo, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  ErrorState,
  Icon,
  PageHeader,
  Skeleton,
  TabStrip,
  useToast,
  type TabStripItem,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { downloadExport, getSummary, listRegisters } from "../api";
import { REGISTER_TYPE_LABEL } from "../tokens";
import { ImportRisksDialog } from "./import-risks-dialog";
import { RiskFormDialog } from "./risk-form-dialog";
import { rememberRegister, rememberedRegister, type RisksOutlet } from "./risks-outlet";
import { SoonBadge } from "./soon";

const TABS: TabStripItem[] = [
  { id: "/risks/overview", label: "Overview" },
  { id: "/risks", label: "Register", end: true },
  { id: "/risks/library", label: "Library" },
  { id: "/risks/assessments", label: "Assessments", soon: true },
  { id: "/risks/indicators", label: "KRIs", soon: true },
  { id: "/risks/settings", label: "Settings" },
];

/**
 * The module root. A workspace can keep several registers, each configured on
 * its own, so the header carries the register switcher and every tab below it
 * works inside the chosen register. The choice is remembered per browser.
 */
export function RisksLayout() {
  const { principal } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const canManage = hasPermission(principal, "risks:manage");
  const canConfigure = hasPermission(principal, "risks:configure");
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(() => rememberedRegister());

  const registersQuery = useQuery({ queryKey: ["risk-registers"], queryFn: listRegisters });
  const registers = useMemo(() => registersQuery.data ?? [], [registersQuery.data]);
  const register =
    registers.find((r) => r.id === selectedId) ?? registers.find((r) => r.is_default) ?? registers[0];

  useEffect(() => {
    if (register && register.id !== selectedId) setSelectedId(register.id);
  }, [register, selectedId]);

  const summaryQuery = useQuery({
    queryKey: ["risk-summary", register?.id],
    queryFn: () => getSummary(register!.id),
    enabled: Boolean(register),
  });

  const selectRegister = (id: string) => {
    setSelectedId(id);
    rememberRegister(id);
  };

  const summary = summaryQuery.data;
  const subtitle = register
    ? [
        register.name,
        summary ? `${summary.total} open ${summary.total === 1 ? "risk" : "risks"}` : null,
        summary?.attention.no_controls ? `${summary.attention.no_controls} without controls` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Risk register";

  const exportAs = (format: "csv" | "xlsx") => {
    if (!register) return;
    downloadExport(register.id, format, {}).catch(() =>
      toast({ title: "The export could not be downloaded. Try again.", tone: "danger" }),
    );
  };

  const tabs = TABS.map((t) =>
    t.id === "/risks" && summary ? { ...t, count: summary.total || undefined } : t,
  );

  return (
    <div className="w-full">
      <PageHeader
        title="Risks"
        icon="risk"
        subtitle={subtitle}
        actions={
          register ? (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" aria-label="Choose register">
                    <Icon name="layers" className="size-4" />
                    <span className="max-w-[12rem] truncate">{register.name}</span>
                    <Icon name="chev" className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-72">
                  <DropdownMenuLabel>Registers</DropdownMenuLabel>
                  {registers
                    .filter((r) => r.status === "active")
                    .map((r) => (
                      <DropdownMenuItem key={r.id} onSelect={() => selectRegister(r.id)}>
                        <span className="flex min-w-0 flex-1 flex-col">
                          <span className="truncate text-body-sm font-semibold text-text-primary">{r.name}</span>
                          <span className="truncate text-caption text-text-subtle">
                            {REGISTER_TYPE_LABEL[r.register_type]} · {r.risk_count} risks · {r.likelihood_levels}×
                            {r.impact_levels}
                          </span>
                        </span>
                        {r.id === register.id ? <Icon name="check" className="size-4 text-action-accent" /> : null}
                      </DropdownMenuItem>
                    ))}
                  {canConfigure ? (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onSelect={() => navigate("/risks/settings")}>
                        <Icon name="gear" className="size-4 text-text-subtle" />
                        Manage registers
                      </DropdownMenuItem>
                    </>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary">
                    <Icon name="export" className="size-4" />
                    Export
                    <Icon name="chev" className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-60">
                  <DropdownMenuItem onSelect={() => exportAs("xlsx")}>
                    <Icon name="spreadsheet" className="size-4 text-text-subtle" />
                    Excel with heatmaps
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => exportAs("csv")}>
                    <Icon name="doc" className="size-4 text-text-subtle" />
                    CSV
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem disabled>
                    <Icon name="report" className="size-4 text-text-subtle" />
                    Board report PDF
                    <span className="ml-auto">
                      <SoonBadge />
                    </span>
                  </DropdownMenuItem>
                  <DropdownMenuItem disabled>
                    <Icon name="camera" className="size-4 text-text-subtle" />
                    Snapshot
                    <span className="ml-auto">
                      <SoonBadge />
                    </span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              {canManage ? (
                <>
                  <Button variant="secondary" onClick={() => setImportOpen(true)}>
                    <Icon name="upload" className="size-4" />
                    Import
                  </Button>
                  <Button onClick={() => setFormOpen(true)}>
                    <Icon name="plus" className="size-4" />
                    Add risk
                  </Button>
                </>
              ) : null}
            </>
          ) : null
        }
      />
      <TabStrip label="Risk sections" items={tabs} variant="bar" />

      {registersQuery.isError ? (
        <ErrorState
          title={describeError(registersQuery.error, "risk registers").title}
          description={describeError(registersQuery.error, "risk registers").message}
          onRetry={() => void registersQuery.refetch()}
        />
      ) : !register ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[4.75rem] w-full" />
            ))}
          </div>
          <Skeleton className="h-80 w-full" />
        </div>
      ) : (
        <>
          <Outlet
            context={
              {
                register,
                registers,
                selectRegister,
                addRisk: () => setFormOpen(true),
                openImport: () => setImportOpen(true),
                canManage,
                canConfigure,
              } satisfies RisksOutlet
            }
          />
          <RiskFormDialog open={formOpen} onOpenChange={setFormOpen} registers={registers} register={register} />
          <ImportRisksDialog open={importOpen} onOpenChange={setImportOpen} register={register} />
        </>
      )}
    </div>
  );
}
