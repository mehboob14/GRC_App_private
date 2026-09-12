import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  Icon,
  PersonSelect,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextField,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { checkDuplicates, createVendor, listMembers, updateVendor } from "../api";
import type { DuplicateMatch, VendorCreateInput, VendorDetail } from "../types";
import { DATA_CLASSIFICATIONS, VENDOR_TYPES } from "../types";
import { CLASSIFICATION_META, duplicateReason, VENDOR_TYPE_LABEL } from "../tokens";

/** Radix Select has no empty-string value, so absence needs a sentinel. */
const NONE = "__none__";

type FormState = {
  name: string;
  vendor_type: string;
  industry: string;
  website: string;
  business_unit: string;
  services_provided: string;
  stores_pii: boolean;
  data_location: string;
  data_classification: string;
  business_owner_membership_id: string | null;
  security_owner_membership_id: string | null;
  relationship_owner_membership_id: string | null;
  engagement_name: string;
};

const BLANK: FormState = {
  name: "",
  vendor_type: "vendor",
  industry: "",
  website: "",
  business_unit: "",
  services_provided: "",
  stores_pii: false,
  data_location: "",
  data_classification: "",
  business_owner_membership_id: null,
  security_owner_membership_id: null,
  relationship_owner_membership_id: null,
  engagement_name: "",
};

function fromVendor(v: VendorDetail): FormState {
  return {
    name: v.name,
    vendor_type: v.vendor_type,
    industry: v.industry ?? "",
    website: v.website ?? "",
    business_unit: v.business_unit ?? "",
    services_provided: v.services_provided,
    stores_pii: v.stores_pii,
    data_location: v.data_location ?? "",
    data_classification: v.data_classification ?? "",
    business_owner_membership_id: v.ownership.business_owner_membership_id,
    security_owner_membership_id: v.ownership.security_owner_membership_id,
    relationship_owner_membership_id: v.ownership.relationship_owner_membership_id,
    engagement_name: "",
  };
}

export function VendorFormDrawer({
  open,
  onOpenChange,
  vendor,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present means edit; absent means create. */
  vendor?: VendorDetail;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const editing = vendor !== undefined;

  const [form, setForm] = useState<FormState>(BLANK);
  const [duplicates, setDuplicates] = useState<DuplicateMatch[]>([]);

  useEffect(() => {
    if (open) setForm(vendor ? fromVendor(vendor) : BLANK);
  }, [open, vendor]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });
  const people = (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name }));

  /**
   * The duplicate warning arrives while the name is still being typed, so the
   * reader sees it before the record exists rather than after. Debounced by
   * hand — this is one field, not a search surface worth a hook.
   */
  useEffect(() => {
    const name = form.name.trim();
    if (editing || name.length < 3) {
      setDuplicates([]);
      return;
    }
    let live = true;
    const timer = window.setTimeout(() => {
      void checkDuplicates(name, form.website || null)
        .then((matches) => {
          if (live) setDuplicates(matches);
        })
        .catch(() => {
          // A failed duplicate check must not block the form. Worst case the
          // reader adds a duplicate, which the register then shows.
          if (live) setDuplicates([]);
        });
    }, 350);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [form.name, form.website, editing]);

  const save = useMutation({
    mutationFn: async (): Promise<VendorDetail> => {
      const body: VendorCreateInput = {
        name: form.name.trim(),
        vendor_type: form.vendor_type,
        industry: form.industry.trim() || null,
        website: form.website.trim() || null,
        business_unit: form.business_unit.trim() || null,
        services_provided: form.services_provided.trim(),
        stores_pii: form.stores_pii,
        data_location: form.data_location.trim() || null,
        data_classification: form.data_classification || null,
        business_owner_membership_id: form.business_owner_membership_id,
        security_owner_membership_id: form.security_owner_membership_id,
        relationship_owner_membership_id: form.relationship_owner_membership_id,
        // PATCH /vendors/{id} is a full replacement of VendorWrite, not a merge:
        // every field left out is reset to its default. These two have no
        // control on this form, so omitting them silently emptied the vendor's
        // tags and in-scope data types on every save.
        tags: vendor?.tags ?? [],
        data_types_in_scope: vendor?.data_types_in_scope ?? [],
      };
      if (editing) return updateVendor(vendor.id, body);
      if (form.engagement_name.trim()) body.engagement = { name: form.engagement_name.trim() };
      return createVendor(body);
    },
    onSuccess: (next) => {
      queryClient.setQueryData(["vendor", next.id], next);
      void queryClient.invalidateQueries({ queryKey: ["vendors"] });
      void queryClient.invalidateQueries({ queryKey: ["vendor-facets"] });
      toast({ title: editing ? "Vendor updated" : "Vendor added", tone: "success" });
      onOpenChange(false);
      if (!editing) navigate(`/vendors/${next.id}`);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "vendor"), tone: "danger" }),
  });

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent size="lg">
        <DrawerHeader>
          <DrawerTitle>{editing ? "Edit vendor" : "Add vendor"}</DrawerTitle>
          <DrawerDescription>
            {editing
              ? "The tier, the residual score and the lifecycle are derived — they are not edited here."
              : "Name the third party and who owns the relationship. Tiering comes next, on the engagement."}
          </DrawerDescription>
        </DrawerHeader>

        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={(e) => {
            e.preventDefault();
            if (form.name.trim()) save.mutate();
          }}
        >
          <DrawerBody className="space-y-3.5">
            <TextField
              label="Name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Acme Analytics"
              autoFocus
            />

            {duplicates.length > 0 ? (
              <div className="rounded-md border border-status-warning-border bg-status-warning-bg p-3">
                <p className="flex items-center gap-1.5 text-label-sm text-status-warning-text">
                  <Icon name="alert" className="size-4 shrink-0" />
                  {duplicates.length === 1
                    ? "A vendor with a similar name already exists"
                    : `${duplicates.length} vendors with similar names already exist`}
                </p>
                <ul className="mt-2 space-y-1">
                  {duplicates.map((d) => (
                    <li key={d.id} className="text-body-sm text-text-secondary">
                      <button
                        type="button"
                        className="font-semibold underline underline-offset-2 hover:text-text-primary"
                        onClick={() => {
                          onOpenChange(false);
                          navigate(`/vendors/${d.id}`);
                        }}
                      >
                        {d.name}
                      </button>
                      <span className="text-text-subtle"> — {duplicateReason(d.reason)}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-caption text-text-subtle">
                  Adding another record is still allowed. Open the existing one first if this is the
                  same organisation under a different name.
                </p>
              </div>
            ) : null}

            <div className="grid gap-3.5 sm:grid-cols-2">
              <SelectField label="Type">
                <Select value={form.vendor_type} onValueChange={(v) => set("vendor_type", v)}>
                  <SelectTrigger aria-label="Vendor type" />
                  <SelectContent>
                    {VENDOR_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {VENDOR_TYPE_LABEL[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <TextField
                label="Industry"
                optional
                value={form.industry}
                onChange={(e) => set("industry", e.target.value)}
                placeholder="Marketing analytics"
              />
            </div>

            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Website"
                optional
                type="url"
                value={form.website}
                onChange={(e) => set("website", e.target.value)}
                placeholder="https://acme.example"
              />
              <TextField
                label="Business unit"
                optional
                value={form.business_unit}
                onChange={(e) => set("business_unit", e.target.value)}
                placeholder="Marketing"
              />
            </div>

            <TextField
              label="Services provided"
              optional
              hint="What this vendor actually does for you. It is what a reviewer reads first."
              value={form.services_provided}
              onChange={(e) => set("services_provided", e.target.value)}
              placeholder="Campaign attribution and reporting"
            />

            <div className="rounded-md border border-border bg-surface-sunken p-3.5">
              <p className="type-overline">Data</p>
              <label className="mt-2.5 flex items-start gap-2.5">
                <Checkbox
                  checked={form.stores_pii}
                  onCheckedChange={(v) => set("stores_pii", v)}
                  id="vendor-stores-pii"
                />
                <span>
                  <span className="text-body-md text-text-primary">
                    This vendor holds personal data
                  </span>
                  <span className="mt-0.5 block text-caption text-text-subtle">
                    Raises the data-sensitivity weight when the engagement is tiered.
                  </span>
                </span>
              </label>
              <div className="mt-3 grid gap-3.5 sm:grid-cols-2">
                <SelectField label="Classification" optional>
                  <Select
                    value={form.data_classification || NONE}
                    onValueChange={(v) => set("data_classification", v === NONE ? "" : v)}
                  >
                    <SelectTrigger aria-label="Data classification" />
                    <SelectContent>
                      <SelectItem value={NONE}>Not classified</SelectItem>
                      {DATA_CLASSIFICATIONS.map((c) => (
                        <SelectItem key={c} value={c}>
                          {CLASSIFICATION_META[c].label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                <TextField
                  label="Data location"
                  optional
                  value={form.data_location}
                  onChange={(e) => set("data_location", e.target.value)}
                  placeholder="EU (Frankfurt)"
                />
              </div>
            </div>

            <div className="rounded-md border border-border bg-surface-sunken p-3.5">
              <p className="type-overline">Ownership</p>
              <p className="mt-1 text-caption text-text-subtle">
                Three separate jobs. The business owner answers for the relationship, security
                reviews the answers, and the relationship owner runs the commercial side.
              </p>
              <div className="mt-3 space-y-3">
                <OwnerField
                  label="Business owner"
                  people={people}
                  value={form.business_owner_membership_id}
                  onChange={(v) => set("business_owner_membership_id", v)}
                />
                <OwnerField
                  label="Security owner"
                  people={people}
                  value={form.security_owner_membership_id}
                  onChange={(v) => set("security_owner_membership_id", v)}
                />
                <OwnerField
                  label="Relationship owner"
                  people={people}
                  value={form.relationship_owner_membership_id}
                  onChange={(v) => set("relationship_owner_membership_id", v)}
                />
              </div>
            </div>

            {!editing ? (
              <TextField
                label="First engagement"
                optional
                hint="The lifecycle runs per engagement, so one is needed before tiering. You can add it later."
                value={form.engagement_name}
                onChange={(e) => set("engagement_name", e.target.value)}
                placeholder="Campaign attribution"
              />
            ) : null}
          </DrawerBody>

          <DrawerFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending} disabled={!form.name.trim()}>
              {editing ? "Save changes" : "Add vendor"}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}

function OwnerField({
  label,
  people,
  value,
  onChange,
}: {
  label: string;
  people: { id: string; name: string }[];
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-label-sm text-text-secondary">{label}</p>
      <PersonSelect
        people={people}
        value={value}
        onChange={onChange}
        placeholder="Unassigned"
        clearLabel="Unassigned"
        aria-label={label}
      />
    </div>
  );
}
