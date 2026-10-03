import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  BrandMark,
  Button,
  ErrorBanner,
  ErrorState,
  Icon,
  Skeleton,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { readableAccent } from "@/lib/color";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { tenantsApi } from "../api";
import { describeProviderError } from "../errors";
import { providerKeys, useTenantBranding, useTenantLogo } from "../hooks";
import { blankToNull } from "../tokens";
import type { Branding, BrandingPut } from "../types";
import { useTenantOutlet } from "./tenant-outlet";

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
const LOGO_MAX_BYTES = 512 * 1024;
const LOGO_TYPES = ["image/png", "image/jpeg", "image/webp"];

const colour = z
  .string()
  .trim()
  .refine((value) => value === "" || HEX_COLOR.test(value), "Use a hex colour like #0369a1.");

const schema = z.object({
  primary_color: colour,
  secondary_color: colour,
  document_footer: z.string().max(1000, "Keep the footer under 1,000 characters."),
  email_from_name: z.string().max(200, "Keep the name under 200 characters."),
  email_from_address: z
    .string()
    .trim()
    .max(320)
    .refine(
      (value) => value === "" || z.string().email().safeParse(value).success,
      "Enter a valid email, like no-reply@company.com.",
    ),
});

type FormValues = z.infer<typeof schema>;

function toForm(branding: Branding): FormValues {
  return {
    primary_color: branding.primary_color ?? "",
    secondary_color: branding.secondary_color ?? "",
    document_footer: branding.document_footer ?? "",
    email_from_name: branding.email_from_name ?? "",
    email_from_address: branding.email_from_address ?? "",
  };
}

/**
 * The save is a full replace, so what the form does not edit has to ride along:
 * the logo reference (set by upload, not by this form) and the custom domain (no
 * screen for it yet) come from the latest saved record, never from a stale copy.
 */
function toPut(values: FormValues, saved: Branding): BrandingPut {
  return {
    logo_ref: saved.logo_ref,
    custom_domain: saved.custom_domain,
    primary_color: blankToNull(values.primary_color)?.toLowerCase() ?? null,
    secondary_color: blankToNull(values.secondary_color)?.toLowerCase() ?? null,
    document_footer: blankToNull(values.document_footer),
    email_from_name: blankToNull(values.email_from_name),
    email_from_address: blankToNull(values.email_from_address),
  };
}

export function TenantBrandingTab() {
  const { tenant } = useTenantOutlet();
  const query = useTenantBranding(tenant.id);

  if (query.isLoading) {
    return <Skeleton className="h-[480px] w-full max-w-[880px] rounded-lg" />;
  }
  if (query.isError || !query.data) {
    const failure = describeProviderError(query.error, "branding");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  return <BrandingForm tenantId={tenant.id} branding={query.data} />;
}

function BrandingForm({
  tenantId,
  branding,
}: {
  tenantId: string;
  branding: Branding;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: toForm(branding),
    resetOptions: { keepDirtyValues: true },
    mode: "onTouched",
  });

  const save = useMutation({
    mutationFn: (values: FormValues) =>
      tenantsApi.saveBranding(tenantId, toPut(values, branding)),
    onSuccess: (updated) => {
      queryClient.setQueryData(providerKeys.branding(tenantId), updated);
      form.reset(toForm(updated));
      toast({ title: "Branding saved", tone: "success" });
    },
  });

  const failure = save.isError ? describeProviderError(save.error, "branding") : null;
  const alertRef = useAlertFocus(Boolean(failure));
  const { errors, isDirty } = form.formState;
  const primary = form.watch("primary_color").trim();
  const shown = HEX_COLOR.test(primary) ? readableAccent(primary) : undefined;

  return (
    <div className="max-w-[880px] space-y-6">
      <LogoCard tenantId={tenantId} branding={branding} />

      <form
        noValidate
        className="space-y-6 rounded-lg border border-border bg-surface-primary p-5 sm:p-6"
        onSubmit={(event) =>
          void form.handleSubmit((values) => save.mutate(values))(event)
        }
      >
        {failure ? (
          <ErrorBanner ref={alertRef} title={failure.title}>
            {failure.message}
          </ErrorBanner>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <ColorField
            label="Primary colour"
            error={errors.primary_color?.message}
            hint={
              shown === undefined
                ? "Buttons, links and the active item use this."
                : shown === null
                  ? "Too light to read text on. Verity blue is used instead."
                  : shown !== primary.toLowerCase()
                    ? `Darkened to ${shown} so text stays readable.`
                    : "Buttons, links and the active item use this."
            }
            value={form.watch("primary_color")}
            registration={form.register("primary_color")}
            onPick={(value) =>
              form.setValue("primary_color", value, {
                shouldDirty: true,
                shouldValidate: true,
              })
            }
          />
          <ColorField
            label="Secondary colour"
            error={errors.secondary_color?.message}
            hint="Stored with the branding. Not used in the app yet."
            value={form.watch("secondary_color")}
            registration={form.register("secondary_color")}
            onPick={(value) =>
              form.setValue("secondary_color", value, {
                shouldDirty: true,
                shouldValidate: true,
              })
            }
          />
        </div>

        <TextArea
          label="Document footer"
          optional
          rows={3}
          maxLength={1000}
          showCount
          hint="Printed at the end of exported reports."
          error={errors.document_footer?.message}
          {...form.register("document_footer")}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Email from name"
            optional
            placeholder="Acme Compliance"
            error={errors.email_from_name?.message}
            {...form.register("email_from_name")}
          />
          <TextField
            label="Email from address"
            optional
            type="email"
            inputMode="email"
            placeholder="no-reply@acme.example"
            error={errors.email_from_address?.message}
            {...form.register("email_from_address")}
          />
        </div>

        <div className="flex justify-end">
          <Button type="submit" size="lg" loading={save.isPending} disabled={!isDirty}>
            Save branding
          </Button>
        </div>
      </form>
    </div>
  );
}

/** A hex field with the browser's own colour picker beside it. */
function ColorField({
  label,
  value,
  hint,
  error,
  registration,
  onPick,
}: {
  label: string;
  value: string;
  hint: string;
  error?: string;
  registration: UseFormRegisterReturn;
  onPick: (value: string) => void;
}) {
  const swatch = HEX_COLOR.test(value.trim()) ? value.trim() : "#ffffff";
  return (
    <TextField
      label={label}
      optional
      placeholder="#0369a1"
      autoComplete="off"
      spellCheck={false}
      hint={hint}
      error={error}
      trailing={
        <input
          type="color"
          aria-label={`${label} picker`}
          value={swatch}
          onChange={(event) => onPick(event.target.value)}
          className="size-6 cursor-pointer rounded-xs border border-border bg-transparent p-0"
        />
      }
      {...registration}
    />
  );
}

/**
 * The logo applies the moment it is uploaded, on its own request: it is a file,
 * and the form below is text. Removing it is just as immediate.
 */
function LogoCard({
  tenantId,
  branding,
}: {
  tenantId: string;
  branding: Branding;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [refusal, setRefusal] = useState<string | null>(null);
  const logo = useTenantLogo(tenantId, branding.logo_ref);

  const apply = (updated: Branding, message: string) => {
    queryClient.setQueryData(providerKeys.branding(tenantId), updated);
    toast({ title: message, tone: "success" });
  };

  const upload = useMutation({
    mutationFn: (file: File) => tenantsApi.uploadLogo(tenantId, file),
    onSuccess: (updated) => apply(updated, "Logo updated"),
  });
  const remove = useMutation({
    mutationFn: () => tenantsApi.removeLogo(tenantId),
    onSuccess: (updated) => apply(updated, "Logo removed"),
  });

  function choose(file: File | undefined) {
    if (input.current) input.current.value = "";
    if (!file) return;
    // The API checks all of this again from the bytes; this only spares a round trip.
    if (!LOGO_TYPES.includes(file.type)) {
      setRefusal("Use a PNG, JPEG or WebP image. SVG files are not accepted.");
    } else if (file.size > LOGO_MAX_BYTES) {
      setRefusal("That logo is larger than 512 KB. Resize it and try again.");
    } else {
      setRefusal(null);
      upload.mutate(file);
    }
  }

  const failure = upload.isError
    ? describeProviderError(upload.error, "logo")
    : remove.isError
      ? describeProviderError(remove.error, "logo")
      : null;
  const message = refusal ?? failure?.message ?? null;

  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5 sm:p-6">
      <h2 className="font-display text-heading-sm text-text-primary">Logo</h2>
      <div className="mt-4 flex flex-wrap items-center gap-5">
        <div className="grid h-20 w-48 shrink-0 place-items-center overflow-hidden rounded-md border border-border bg-surface-sunken p-2">
          {logo.data ? (
            <img
              src={logo.data}
              alt="Workspace logo"
              className="max-h-full max-w-full object-contain"
            />
          ) : branding.logo_ref && logo.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <div className="flex items-center gap-2 text-caption text-text-subtle">
              <BrandMark size={24} />
              None set
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              loading={upload.isPending}
              disabled={remove.isPending}
              onClick={() => input.current?.click()}
            >
              <Icon name="upload" className="size-4" />
              {branding.logo_ref ? "Replace logo" : "Upload logo"}
            </Button>
            {branding.logo_ref ? (
              <Button
                variant="ghost"
                loading={remove.isPending}
                disabled={upload.isPending}
                onClick={() => remove.mutate()}
              >
                Remove
              </Button>
            ) : null}
          </div>
          <p className="mt-2 text-body-sm text-text-subtle">
            PNG, JPEG or WebP, up to 512 KB.
          </p>
          {message ? (
            <p
              role="alert"
              className="mt-1.5 flex items-start gap-1 text-body-sm text-status-danger-text"
            >
              <Icon name="alert" className="mt-px size-3.5 shrink-0" />
              {message}
            </p>
          ) : null}
        </div>
        <input
          ref={input}
          type="file"
          accept={LOGO_TYPES.join(",")}
          className="hidden"
          aria-label="Choose a logo file"
          onChange={(event) => choose(event.target.files?.[0])}
        />
      </div>
    </section>
  );
}
