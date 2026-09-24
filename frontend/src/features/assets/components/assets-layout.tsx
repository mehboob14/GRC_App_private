import { useRef, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Icon,
  PageHeader,
  TabStrip,
  useToast,
  type TabStripItem,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { assetImportTemplateCsv, assetsExportCsv, downloadCsv, getSummary, listAssets } from "../api";
import { AssetFormDrawer } from "./asset-form-drawer";
import type { AssetsOutlet, RegisterView } from "./assets-outlet";

/** Assets is a small workspace: the register is the day-to-day inventory,
 *  Overview is the read on the whole estate. Detail and import sit outside
 *  this strip — they are drill-downs, not tabs. */
const TABS: TabStripItem[] = [
  { id: "/assets/overview", label: "Overview" },
  { id: "/assets", label: "Register", end: true },
  { id: "/assets/settings", label: "Settings" },
];

export function AssetsLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [formOpen, setFormOpen] = useState(false);
  const registerView = useRef<RegisterView | null>(null);

  // Same query key the register and overview use, so react-query serves it from
  // cache — the tab count costs no extra request.
  const summaryQuery = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });
  const summary = summaryQuery.data;
  const subtitle = summary
    ? [
        `${summary.total} ${summary.total === 1 ? "asset" : "assets"}`,
        summary.by_tier.critical ? `${summary.by_tier.critical} critical` : null,
        summary.needs_cia ? `${summary.needs_cia} missing CIA` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Asset inventory";

  const tabs = TABS.map((t) => (t.id === "/assets" ? { ...t, count: summary?.total } : t));

  const onSaved = () => {
    queryClient.invalidateQueries({ queryKey: ["assets"] });
    queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
    queryClient.invalidateQueries({ queryKey: ["asset-facets"] });
  };

  // No backend export endpoint for assets yet: fetch the page the register is
  // showing, with its filters. From Overview that is the register's first page.
  const exportCsv = () => {
    const view = registerView.current;
    listAssets(view?.filters ?? {}, view?.page, view?.pageSize)
      .then((res) => downloadCsv("assets.csv", assetsExportCsv(res.items)))
      .catch((error) => toast({ title: errorToast(error, "asset register"), tone: "danger" }));
  };

  return (
    <div className="w-full">
      <PageHeader
        title="Assets"
        icon="box"
        subtitle={subtitle}
        actions={
          <>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary">
                  <Icon name="export" className="size-4" />
                  Export
                  <Icon name="chev" className="size-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onSelect={exportCsv}>
                  <Icon name="download" className="size-4 text-text-subtle" />
                  CSV
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => downloadCsv("asset-import-template.csv", assetImportTemplateCsv())}>
                  <Icon name="spreadsheet" className="size-4 text-text-subtle" />
                  Import template
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="secondary" onClick={() => navigate("/assets/import")}>
              <Icon name="upload" className="size-4" />
              Import
            </Button>
            <Button onClick={() => setFormOpen(true)}>
              <Icon name="plus" className="size-4" />
              Add asset
            </Button>
          </>
        }
      />
      <TabStrip label="Asset sections" items={tabs} variant="bar" />
      <Outlet context={{ addAsset: () => setFormOpen(true), registerView } satisfies AssetsOutlet} />
      <AssetFormDrawer open={formOpen} onOpenChange={setFormOpen} onSaved={onSaved} />
    </div>
  );
}
