import { apiFetch } from "@/lib/api/client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  CountryMultiSelect,
  CountrySelect,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  PersonSelect,
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Skeleton,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import { iamApi, tenantApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type {
  CompanyProfile,
  ProfileAnswer,
  ProfileAnswers,
  ProfileQuestion,
  ProfileSection,
} from "@/lib/api/types";

/**
 * The typed half of the company profile (guided onboarding PR-1 to PR-6).
 *
 * The questions come from the server, which validates answers against the same list, so
 * the form can never offer an option the server refuses. Each question says in one line
 * what reads its answer. Answers save as a draft; an admin then confirms the profile, which
 * freezes a version. Editing a confirmed profile makes it a draft again.
 */

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** Answers in the earlier free text fields, offered as a hint until the question is answered. */
function legacyHint(question: ProfileQuestion, profile: CompanyProfile): string | null {
  const earlier: Record<string, string | null> = {
    industry: profile.industry,
    headcount_band: profile.company_size,
    hq_country: profile.headquarters,
  };
  const value = earlier[question.key];
  return value ? `From your earlier profile: ${value}` : null;
}

function shown(question: ProfileQuestion, answers: ProfileAnswers): boolean {
  if (question.show_if.length === 0) return true;
  return question.show_if.some((rule) => {
    const value = answers[rule.key];
    if (rule.contains !== null) return Array.isArray(value) && value.includes(rule.contains);
    return typeof value === "string" && rule.equals.includes(value);
  });
}

function sameAnswers(a: ProfileAnswers, b: ProfileAnswers): boolean {
  return JSON.stringify(a, Object.keys(a).sort()) === JSON.stringify(b, Object.keys(b).sort());
}

function patchFrom(saved: ProfileAnswers, draft: ProfileAnswers): Record<string, ProfileAnswer | null> {
  const patch: Record<string, ProfileAnswer | null> = {};
  for (const key of new Set([...Object.keys(saved), ...Object.keys(draft)])) {
    const before = saved[key];
    const after = draft[key];
    if (JSON.stringify(before) !== JSON.stringify(after)) patch[key] = after ?? null;
  }
  return patch;
}

function QuestionField({
  question,
  value,
  onChange,
  disabled,
  hint,
  firstCountry,
}: {
  question: ProfileQuestion;
  value: ProfileAnswer | undefined;
  onChange: (value: ProfileAnswer | undefined) => void;
  disabled: boolean;
  hint: string | null;
  firstCountry: string | null;
}) {
  const id = `profile-${question.key}`;
  const label = (
    <span id={`${id}-label`} className="font-sans text-label-sm text-text-secondary">
      {question.label}
      {question.core ? null : <span className="text-text-subtle"> (optional)</span>}
    </span>
  );
  const help = (
    <span className="text-caption text-text-subtle">
      {hint ? `${hint}. ` : null}
      {question.used_for}
    </span>
  );
  const asList = Array.isArray(value) ? value : [];

  let control: ReactNode;
  switch (question.kind) {
    case "text":
      return (
        <TextArea
          id={id}
          label={question.label}
          optional={!question.core}
          hint={question.used_for}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value || undefined)}
          maxLength={400}
          rows={2}
          disabled={disabled}
        />
      );
    case "country":
      control = (
        <CountrySelect
          value={typeof value === "string" ? value : null}
          onChange={(code) => onChange(code ?? undefined)}
          disabled={disabled}
          aria-label={question.label}
        />
      );
      break;
    case "countries":
    case "regions":
      control = (
        <CountryMultiSelect
          value={asList}
          onChange={(codes) => onChange(codes.length ? codes : undefined)}
          withRegions={question.kind === "regions"}
          first={firstCountry}
          disabled={disabled}
          aria-label={question.label}
        />
      );
      break;
    case "month":
      control = (
        <Select
          value={typeof value === "number" ? String(value) : ""}
          onValueChange={(v) => onChange(Number(v))}
          disabled={disabled}
        >
          <SelectTrigger aria-labelledby={`${id}-label`} />
          <SelectContent>
            {MONTHS.map((month, index) => (
              <SelectItem key={month} value={String(index + 1)}>
                {month}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
      break;
    case "many":
      control = (
        <div role="group" aria-labelledby={`${id}-label`} className="grid gap-2 sm:grid-cols-2">
          {question.options.map((option) => {
            const checked = asList.includes(option.value);
            const toggle = (on: boolean) => {
              let next = on ? [...asList, option.value] : asList.filter((v) => v !== option.value);
              // "None" stands alone: picking it clears the rest, picking anything clears it.
              if (on && option.value === "none") next = ["none"];
              else if (on) next = next.filter((v) => v !== "none");
              onChange(next.length ? next : undefined);
            };
            return (
              <label key={option.value} className="flex items-center gap-2 text-body-md text-text-primary">
                <Checkbox checked={checked} onCheckedChange={(v) => toggle(v === true)} disabled={disabled} />
                {option.label}
              </label>
            );
          })}
        </div>
      );
      break;
    default:
      // "one" and "tri": a row of radios when short, a select when long.
      control =
        question.options.length <= 6 ? (
          <RadioGroup
            aria-labelledby={`${id}-label`}
            value={typeof value === "string" ? value : ""}
            onValueChange={(v) => onChange(v)}
            disabled={disabled}
            className="flex-row flex-wrap gap-x-5 gap-y-2"
          >
            {question.options.map((option) => (
              <RadioGroupItem key={option.value} value={option.value} label={option.label} />
            ))}
          </RadioGroup>
        ) : (
          <Select
            value={typeof value === "string" ? value : ""}
            onValueChange={(v) => onChange(v)}
            disabled={disabled}
          >
            <SelectTrigger aria-labelledby={`${id}-label`} />
            <SelectContent>
              {question.options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
  }
  return (
    <div className="flex flex-col gap-1.5">
      {label}
      {control}
      {help}
    </div>
  );
}

function HistoryDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { principal } = useAuth();
  const versions = useQuery({
    queryKey: ["company-profile-versions", principal?.tenant_id],
    queryFn: tenantApi.getProfileVersions,
    enabled: open,
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Confirmed versions</DialogTitle>
        </DialogHeader>
        <DialogBody>
          {versions.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (versions.data ?? []).length === 0 ? (
            <p className="text-body-sm text-text-secondary">No version has been confirmed yet.</p>
          ) : (
            <ul className="space-y-2">
              {(versions.data ?? []).map((v) => (
                <li key={v.version} className="flex justify-between text-body-sm">
                  <span className="font-semibold text-text-primary">Version {v.version}</span>
                  <span className="text-text-secondary">{new Date(v.confirmed_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}

export function ProfileQuestions({ profile, canManage }: { profile: CompanyProfile; canManage: boolean }) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const questions = useQuery({
    queryKey: ["company-profile-questions"],
    queryFn: tenantApi.getProfileQuestions,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const [draft, setDraft] = useState<ProfileAnswers>(profile.answers);
  const [history, setHistory] = useState(false);
  const prefill = useQuery({
    queryKey: ["profile-prefill", profile.tenant_id],
    queryFn: () =>
      apiFetch<{ key: string; value: ProfileAnswer; source: string }[]>("/onboarding/profile-prefill"),
    enabled: canManage,
  });
  const offered = (prefill.data ?? []).filter((p) => draft[p.key] === undefined);
  const sourceOf = new Map((prefill.data ?? []).map((p) => [p.key, p] as const));
  useEffect(() => setDraft(profile.answers), [profile.answers]);

  const profileKey = ["company-profile", principal?.tenant_id];
  const settle = (updated: CompanyProfile) => {
    queryClient.setQueryData(profileKey, updated);
    void queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
  };
  const save = useMutation({
    mutationFn: () => tenantApi.updateCompanyProfile({ answers: patchFrom(profile.answers, draft) }),
    onSuccess: (updated) => {
      settle(updated);
      toast({ title: "Answers saved", tone: "success" });
    },
  });
  const confirm = useMutation({
    mutationFn: tenantApi.confirmCompanyProfile,
    onSuccess: (updated) => {
      settle(updated);
      void queryClient.invalidateQueries({ queryKey: ["company-profile-versions"] });
      toast({ title: `Version ${updated.version} confirmed`, tone: "success" });
    },
  });

  const dirty = !sameAnswers(draft, profile.answers);
  const sections: ProfileSection[] = useMemo(() => questions.data ?? [], [questions.data]);
  const core = useMemo(
    () => sections.flatMap((s) => s.questions).filter((q) => q.core && shown(q, draft)),
    [sections, draft],
  );
  const coreDone = core.filter((q) => draft[q.key] !== undefined).length;
  const failure = save.isError
    ? describeError(save.error, "answers")
    : confirm.isError
      ? describeError(confirm.error, "profile")
      : null;

  if (questions.isLoading) return <Skeleton className="h-[480px] w-full rounded-lg" />;
  if (questions.isError) {
    return (
      <ErrorBanner title="Couldn’t load the profile questions">
        {describeError(questions.error, "questions").message}
      </ErrorBanner>
    );
  }

  const confirmedOn = profile.confirmed_at ? new Date(profile.confirmed_at).toLocaleDateString() : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface-primary px-5 py-3.5">
        {profile.status === "confirmed" && !dirty ? (
          <StatusPill status="success" label={`Version ${profile.version} confirmed`} />
        ) : (
          <StatusPill status="pending" label="Draft" />
        )}
        <span className="flex-1 text-body-sm text-text-secondary">
          {profile.status === "confirmed" && !dirty
            ? `Confirmed on ${confirmedOn ?? "an earlier date"}.`
            : `${coreDone} of ${core.length} key questions answered.`}
        </span>
        {canManage && offered.length ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setDraft((current) => ({
                ...current,
                ...Object.fromEntries(offered.map((p) => [p.key, p.value])),
              }))
            }
          >
            Fill {offered.length} from your workspace
          </Button>
        ) : null}
        {profile.version > 0 ? (
          <Button variant="ghost" size="sm" onClick={() => setHistory(true)}>
            History
          </Button>
        ) : null}
        {canManage ? (
          dirty ? (
            <Button loading={save.isPending} onClick={() => save.mutate()}>
              Save answers
            </Button>
          ) : profile.status !== "confirmed" ? (
            <Button
              loading={confirm.isPending}
              disabled={coreDone < core.length}
              onClick={() => confirm.mutate()}
            >
              Confirm profile
            </Button>
          ) : null
        ) : null}
      </div>

      {failure ? <ErrorBanner title={failure.title}>{failure.message}</ErrorBanner> : null}

      {sections.map((section) => {
        const visible = section.questions.filter((q) => shown(q, draft));
        if (visible.length === 0) return null;
        return (
          <section
            key={section.key}
            aria-labelledby={`profile-section-${section.key}`}
            className="rounded-lg border border-border bg-surface-primary p-5 sm:p-6"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h3 id={`profile-section-${section.key}`} className="font-display text-title-md text-text-primary">
                {section.title}
              </h3>
              {canManage ? <AskSomeone section={section.key} title={section.title} /> : null}
            </div>
            <div className="grid gap-5">
              {visible.map((question) => (
                <QuestionField
                  key={question.key}
                  question={question}
                  value={draft[question.key]}
                  onChange={(next) =>
                    setDraft((current) => {
                      const copy = { ...current };
                      if (next === undefined) delete copy[question.key];
                      else copy[question.key] = next;
                      return copy;
                    })
                  }
                  disabled={!canManage}
                  hint={
                    draft[question.key] === undefined
                      ? legacyHint(question, profile)
                      : profile.answers[question.key] === undefined &&
                          sourceOf.get(question.key) &&
                          JSON.stringify(sourceOf.get(question.key)?.value) === JSON.stringify(draft[question.key])
                        ? `${sourceOf.get(question.key)?.source}. Check it, then save`
                        : null
                  }
                  firstCountry={typeof draft.hq_country === "string" ? draft.hq_country : null}
                />
              ))}
            </div>
          </section>
        );
      })}

      <HistoryDialog open={history} onOpenChange={setHistory} />
    </div>
  );
}

/** Give one section of the profile to a colleague, as a task (guided onboarding 2.8). */
function AskSomeone({ section, title }: { section: string; title: string }) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [person, setPerson] = useState<string | null>(null);
  const members = useQuery({ queryKey: ["members", "profile-ask"], queryFn: () => iamApi.listMembers(), enabled: open });
  const ask = useMutation({
    mutationFn: () =>
      apiFetch<{ raised: number }>(`/onboarding/profile-sections/${section}/assign`, {
        method: "POST",
        body: JSON.stringify({ membership_id: person }),
      }),
    onSuccess: (r) => {
      setOpen(false);
      toast({ title: r.raised ? "Task sent" : "They already have this task", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "task"), tone: "danger" }),
  });
  const people = (members.data ?? [])
    .filter((m) => m.status === "active")
    .map((m) => ({ id: m.membership_id, name: m.full_name, email: m.email }));
  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        Ask someone
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Who should answer {title.toLowerCase()}?</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <PersonSelect people={people} value={person} onChange={setPerson} placeholder="Choose a person" aria-label="Person" />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!person} loading={ask.isPending} onClick={() => ask.mutate()}>
              Send as a task
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
