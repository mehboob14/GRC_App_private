import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { requestIntegration, type Capability } from "../api";
import { refreshAutomation } from "../hooks";

const ANY = "any";

/**
 * Ask for a system Verity cannot connect to yet. The request is kept on the
 * workspace and shows on the control, so nobody asks twice.
 */
export function RequestIntegrationDialog({
  open,
  onOpenChange,
  controlId = null,
  capabilities = [],
  defaultCapability = null,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  controlId?: string | null;
  capabilities?: Pick<Capability, "key" | "name">[];
  defaultCapability?: string | null;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [capability, setCapability] = useState(ANY);
  const [note, setNote] = useState("");

  // Reset only as the dialog opens: the page behind it refetches while a run is
  // in flight, and a new capabilities array must not wipe what is being typed.
  const wasOpen = useRef(false);
  useEffect(() => {
    if (open && !wasOpen.current) {
      setName("");
      setNote("");
      setCapability(defaultCapability ?? capabilities[0]?.key ?? ANY);
    }
    wasOpen.current = open;
  }, [open, defaultCapability, capabilities]);

  const send = useMutation({
    mutationFn: () =>
      requestIntegration({
        provider_name: name.trim(),
        capability_key: capability === ANY ? null : capability,
        control_id: controlId,
        note: note.trim() || null,
      }),
    onSuccess: (request) => {
      refreshAutomation(queryClient);
      void queryClient.invalidateQueries({
        queryKey: ["integration-requests"],
      });
      onOpenChange(false);
      toast({ title: `${request.provider_name} requested`, tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "request"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm" scrollBody>
        <form
          className="flex min-h-0 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            send.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Request an integration</DialogTitle>
            <DialogDescription>
              Name the system you use and we will plan it in.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <TextField
              label="System"
              placeholder="Hexnode"
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
            />
            {capabilities.length > 0 ? (
              <SelectField label="Kind of system">
                <Select value={capability} onValueChange={setCapability}>
                  <SelectTrigger
                    aria-label="Kind of system"
                    className="text-left"
                  />
                  <SelectContent>
                    {capabilities.map((c) => (
                      <SelectItem key={c.key} value={c.key}>
                        {c.name}
                      </SelectItem>
                    ))}
                    <SelectItem value={ANY}>Something else</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
            ) : null}
            <TextArea
              label="What should it prove"
              optional
              rows={3}
              maxLength={2000}
              placeholder="Every laptop is encrypted and enrolled."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </DialogBody>
          <DialogFooter>
            <Button
              variant="secondary"
              type="button"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={send.isPending}
              disabled={!name.trim()}
            >
              <Icon name="mail" className="size-4" />
              Send request
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
