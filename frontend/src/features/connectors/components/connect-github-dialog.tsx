import { useEffect, useState } from "react";
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
  PasswordField,
  TextField,
  useToast,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import { connectGitHub, runConnection } from "../api";
import { refreshAutomation } from "../hooks";

const TOKEN_URL = "https://github.com/settings/personal-access-tokens/new";

/** What the token needs, all read only. Mirrors the connector README. */
const ACCESS: { scope: string; items: string }[] = [
  { scope: "Repository", items: "Metadata, Administration, Pull requests" },
  { scope: "Organization", items: "Administration" },
];

/**
 * Connect a GitHub organisation (or the token owner's own repositories) with a
 * read only token. On success the first run starts straight away, so the
 * controls fill in without another click.
 */
export function ConnectGitHubDialog({
  open,
  onOpenChange,
  onConnected,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: () => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [account, setAccount] = useState("");
  const [token, setToken] = useState("");

  useEffect(() => {
    if (open) {
      setAccount("");
      setToken("");
    }
  }, [open]);

  const connect = useMutation({
    mutationFn: async () => {
      const connection = await connectGitHub(token.trim(), account);
      await runConnection(connection.id);
      return connection;
    },
    onSuccess: (connection) => {
      setToken("");
      refreshAutomation(queryClient);
      onConnected?.();
      onOpenChange(false);
      toast({
        title: `${connection.account_login} connected. First run started.`,
        tone: "success",
      });
    },
  });
  const failure = connect.isError
    ? describeError(connect.error, "connection").message
    : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md" scrollBody>
        <form
          className="flex min-h-0 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            connect.mutate();
          }}
        >
          <DialogHeader>
            <div className="flex items-center gap-3">
              <ConnectorLogo id="github" name="GitHub" size={40} />
              <div>
                <DialogTitle>Connect GitHub</DialogTitle>
                <DialogDescription>
                  Read only. Verity never writes to GitHub.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <DialogBody className="space-y-4">
            <TextField
              label="Organisation"
              placeholder="acme"
              hint="Leave empty to check the token owner's own repositories."
              value={account}
              maxLength={100}
              autoComplete="off"
              onChange={(e) => setAccount(e.target.value)}
            />
            <PasswordField
              label="Access token"
              placeholder="github_pat_"
              value={token}
              autoComplete="off"
              error={failure}
              onChange={(e) => setToken(e.target.value)}
            />

            <section className="rounded-lg border border-border bg-surface-sunken p-3.5">
              <div className="mb-2 flex items-center justify-between gap-3">
                <h3 className="type-overline">Grant read access to</h3>
                <a
                  href={TOKEN_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-label-sm text-action-accent hover:underline"
                >
                  Create a token
                  <Icon name="export" className="size-3.5" />
                </a>
              </div>
              <ul className="space-y-1.5">
                {ACCESS.map((row) => (
                  <li
                    key={row.scope}
                    className="flex items-start gap-2 text-body-sm"
                  >
                    <Icon
                      name="shieldCheck"
                      className="mt-0.5 size-4 shrink-0 text-status-success-text"
                    />
                    <span className="text-text-secondary">
                      <span className="font-semibold text-text-primary">
                        {row.scope}:
                      </span>{" "}
                      {row.items}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
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
              loading={connect.isPending}
              disabled={!token.trim()}
            >
              <Icon name="plug" className="size-4" />
              Connect
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
