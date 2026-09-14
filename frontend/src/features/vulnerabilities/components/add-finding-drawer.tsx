import { useQueryClient } from "@tanstack/react-query";
import { Drawer, DrawerBody, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui";
import { ManualAddFinding } from "./manual-add-finding";

/**
 * The module header's "Add finding" affordance — the shared manual-add form in
 * a right-side drawer, so a finding can be added without leaving the page.
 * On success it refreshes the register/KPIs and closes.
 */
export function AddFindingDrawer({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();

  const onAdded = () => {
    queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
    queryClient.invalidateQueries({ queryKey: ["vuln-kpis"] });
    queryClient.invalidateQueries({ queryKey: ["vuln-all"] });
    onOpenChange(false);
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Add finding</DrawerTitle>
        </DrawerHeader>
        <DrawerBody>
          {/* Remount per open so the form starts empty each time. */}
          {open ? <ManualAddFinding onAdded={onAdded} /> : null}
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}
