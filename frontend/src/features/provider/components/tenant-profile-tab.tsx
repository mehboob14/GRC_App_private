import type { ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Button,
  ErrorBanner,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { tenantsApi } from "../api";
import { describeProviderError } from "../errors";
import { providerKeys } from "../hooks";
import { blankToNull } from "../tokens";
import type { Tenant, TenantUpdate } from "../types";
import { useTenantOutlet } from "./tenant-outlet";

const schema = z.object({
  legal_name: z.string().trim().min(1, "Enter the company's legal name."),
  plan: z.string().trim().min(1, "Enter a plan."),
  trading_name: z.string(),
  industry: z.string(),
  registration_number: z.string(),
  address_line1: z.string(),
  address_line2: z.string(),
  city: z.string(),
  state_region: z.string(),
  postal_code: z.string(),
  country: z.string(),
  primary_contact_name: z.string(),
  primary_contact_email: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || z.string().email().safeParse(value).success,
      "Enter a valid email, like name@company.com.",
    ),
  primary_contact_phone: z.string(),
  onboarded_at: z.string(),
  notes: z.string(),
});

type FormValues = z.infer<typeof schema>;

/** The two columns that can never be blank; everything else clears to null. */
const REQUIRED: readonly (keyof FormValues)[] = ["legal_name", "plan"];

function toForm(tenant: Tenant): FormValues {
  return {
    legal_name: tenant.legal_name,
    plan: tenant.plan,
    trading_name: tenant.trading_name ?? "",
    industry: tenant.industry ?? "",
    registration_number: tenant.registration_number ?? "",
    address_line1: tenant.address_line1 ?? "",
    address_line2: tenant.address_line2 ?? "",
    city: tenant.city ?? "",
    state_region: tenant.state_region ?? "",
    postal_code: tenant.postal_code ?? "",
    country: tenant.country ?? "",
    primary_contact_name: tenant.primary_contact_name ?? "",
    primary_contact_email: tenant.primary_contact_email ?? "",
    primary_contact_phone: tenant.primary_contact_phone ?? "",
    onboarded_at: tenant.onboarded_at ?? "",
    notes: tenant.notes ?? "",
  };
}

/** Only what the operator changed is sent, so a save cannot overwrite someone else's edit. */
function toPatch(
  values: FormValues,
  dirty: Partial<Record<keyof FormValues, boolean | undefined>>,
): TenantUpdate {
  const patch: Record<string, string | null> = {};
  for (const key of Object.keys(dirty) as (keyof FormValues)[]) {
    if (!dirty[key]) continue;
    patch[key] = REQUIRED.includes(key)
      ? values[key].trim()
      : blankToNull(values[key]);
  }
  return patch as TenantUpdate;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 font-display text-heading-sm text-text-primary">
        {title}
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </section>
  );
}

export function TenantProfileTab() {
  const { tenant } = useTenantOutlet();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    // Re-syncs when the tenant is refetched, without discarding what is being typed.
    values: toForm(tenant),
    resetOptions: { keepDirtyValues: true },
    mode: "onTouched",
  });

  const save = useMutation({
    mutationFn: (patch: TenantUpdate) => tenantsApi.update(tenant.id, patch),
    onSuccess: (updated) => {
      queryClient.setQueryData(providerKeys.tenant(tenant.id), updated);
      void queryClient.invalidateQueries({ queryKey: providerKeys.tenantsRoot });
      form.reset(toForm(updated));
      toast({ title: "Profile saved", tone: "success" });
    },
  });

  const failure = save.isError ? describeProviderError(save.error, "tenant") : null;
  const alertRef = useAlertFocus(Boolean(failure));
  const { errors, dirtyFields, isDirty } = form.formState;
  const field = (name: keyof FormValues) => ({
    ...form.register(name),
    error: errors[name]?.message,
  });

  return (
    <form
      noValidate
      className="max-w-[880px] space-y-8 rounded-lg border border-border bg-surface-primary p-5 sm:p-6"
      onSubmit={(event) =>
        void form.handleSubmit((values) =>
          save.mutate(toPatch(values, dirtyFields)),
        )(event)
      }
    >
      {failure ? (
        <ErrorBanner ref={alertRef} title={failure.title}>
          {failure.message}
        </ErrorBanner>
      ) : null}

      <Section title="Company">
        <TextField label="Legal name" {...field("legal_name")} />
        <TextField label="Trading name" optional {...field("trading_name")} />
        <TextField label="Plan" {...field("plan")} />
        <TextField label="Industry" optional {...field("industry")} />
        <TextField
          label="Registration number"
          optional
          {...field("registration_number")}
        />
        <TextField label="Onboarded" optional type="date" {...field("onboarded_at")} />
      </Section>

      <Section title="Address">
        <TextField label="Address line 1" optional {...field("address_line1")} />
        <TextField label="Address line 2" optional {...field("address_line2")} />
        <TextField label="City" optional {...field("city")} />
        <TextField label="State or region" optional {...field("state_region")} />
        <TextField label="Postal code" optional {...field("postal_code")} />
        <TextField label="Country" optional {...field("country")} />
      </Section>

      <Section title="Primary contact">
        <TextField label="Name" optional {...field("primary_contact_name")} />
        <TextField
          label="Email"
          optional
          type="email"
          inputMode="email"
          {...field("primary_contact_email")}
        />
        <TextField
          label="Phone"
          optional
          type="tel"
          {...field("primary_contact_phone")}
        />
      </Section>

      <TextArea
        label="Internal notes"
        optional
        rows={3}
        hint="Only platform operators see these."
        {...form.register("notes")}
      />

      <div className="flex justify-end">
        <Button type="submit" size="lg" loading={save.isPending} disabled={!isDirty}>
          Save profile
        </Button>
      </div>
    </form>
  );
}
