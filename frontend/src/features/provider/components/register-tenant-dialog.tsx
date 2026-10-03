import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  TextField,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { tenantsApi } from "../api";
import { describeProviderError } from "../errors";
import { providerKeys } from "../hooks";
import { SLUG_PATTERN, blankToNull, slugify } from "../tokens";

const schema = z.object({
  legal_name: z.string().trim().min(1, "Enter the company's legal name."),
  slug: z
    .string()
    .min(1, "Enter a workspace address.")
    .regex(
      SLUG_PATTERN,
      "Use lowercase letters, numbers and hyphens, starting and ending with a letter or number.",
    ),
  plan: z.string().trim().min(1, "Enter a plan, for example trial."),
  trading_name: z.string().trim(),
  primary_contact_name: z.string().trim(),
  primary_contact_email: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || z.string().email().safeParse(value).success,
      "Enter a valid email, like name@company.com.",
    ),
});

type FormValues = z.infer<typeof schema>;

const BLANK: FormValues = {
  legal_name: "",
  slug: "",
  plan: "",
  trading_name: "",
  primary_contact_name: "",
  primary_contact_email: "",
};

export function RegisterTenantDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Register tenant</DialogTitle>
          <DialogDescription>
            Creates the workspace. Brand it and invite its first admin next.
          </DialogDescription>
        </DialogHeader>
        {/* Mounted only while open, so every opening starts blank and with a new
            idempotency key. */}
        <RegisterTenantForm onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}

function RegisterTenantForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  // One key per opening: a double click, or a retry after a dropped connection,
  // returns the tenant already created instead of a second one.
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: BLANK,
    mode: "onTouched",
  });

  // The address follows the name until the operator types one of their own.
  const legalName = form.watch("legal_name");
  const slugEdited = Boolean(form.formState.dirtyFields.slug);
  useEffect(() => {
    if (!slugEdited) {
      form.setValue("slug", slugify(legalName), {
        shouldValidate: form.formState.touchedFields.slug === true,
      });
    }
  }, [legalName, slugEdited, form]);

  const register = useMutation({
    mutationFn: (values: FormValues) =>
      tenantsApi.register(
        {
          legal_name: values.legal_name.trim(),
          slug: values.slug,
          plan: values.plan.trim(),
          trading_name: blankToNull(values.trading_name),
          primary_contact_name: blankToNull(values.primary_contact_name),
          primary_contact_email: blankToNull(values.primary_contact_email),
        },
        idempotencyKey,
      ),
    onSuccess: (tenant) => {
      void queryClient.invalidateQueries({ queryKey: providerKeys.tenantsRoot });
      toast({ title: "Tenant registered", tone: "success" });
      onClose();
      navigate(`/provider/tenants/${tenant.id}`);
    },
    onError: (error) => {
      // A taken address belongs to the field that holds it, not to the form.
      if (error instanceof ApiError && error.code === "slug_conflict") {
        form.setError("slug", { message: error.message });
        form.setFocus("slug");
      }
    },
  });

  const slugConflict =
    register.error instanceof ApiError && register.error.code === "slug_conflict";
  const failure =
    register.isError && !slugConflict
      ? describeProviderError(register.error, "workspace")
      : null;
  const alertRef = useAlertFocus(Boolean(failure));

  return (
    <form
      noValidate
      onSubmit={(event) =>
        void form.handleSubmit((values) => register.mutate(values))(event)
      }
    >
      <DialogBody className="space-y-3.5">
        {failure ? (
          <ErrorBanner ref={alertRef} title={failure.title}>
            {failure.message}
          </ErrorBanner>
        ) : null}
        <TextField
          label="Legal name"
          placeholder="Acme Compliance Pty Ltd"
          autoFocus
          error={form.formState.errors.legal_name?.message}
          {...form.register("legal_name")}
        />
        <div className="grid gap-3.5 sm:grid-cols-2">
          <TextField
            label="Workspace address"
            placeholder="acme-compliance"
            autoComplete="off"
            spellCheck={false}
            hint="Lowercase letters, numbers and hyphens."
            error={form.formState.errors.slug?.message}
            {...form.register("slug")}
          />
          <TextField
            label="Plan"
            placeholder="Enterprise"
            autoComplete="off"
            error={form.formState.errors.plan?.message}
            {...form.register("plan")}
          />
        </div>
        <TextField
          label="Trading name"
          optional
          placeholder="Acme"
          {...form.register("trading_name")}
        />
        <div className="grid gap-3.5 sm:grid-cols-2">
          <TextField
            label="Primary contact"
            optional
            placeholder="Jordan Lee"
            {...form.register("primary_contact_name")}
          />
          <TextField
            label="Contact email"
            optional
            type="email"
            inputMode="email"
            placeholder="jordan@acme.example"
            error={form.formState.errors.primary_contact_email?.message}
            {...form.register("primary_contact_email")}
          />
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" loading={register.isPending}>
          Register tenant
        </Button>
      </DialogFooter>
    </form>
  );
}
