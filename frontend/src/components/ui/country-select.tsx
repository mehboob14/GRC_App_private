import { useMemo } from "react";
import { Icon } from "@/components/ui/icon";
import { SearchableSelect, type SearchableOption } from "@/components/ui/searchable-select";
import {
  COUNTRIES,
  REGIONS,
  closestCountries,
  countryName,
  searchCountries,
  type Country,
} from "@/lib/countries";

/**
 * Country pickers: one country, or several as chips. Search ranks exact codes and aliases
 * first (UAE, KSA, UK), then names, and forgives a spelling mistake or two. A two letter code
 * tag stands in for a flag: flag emoji do not render on Windows. Plan: part 3 section 12.
 */

const toOption = (c: Country): SearchableOption => ({
  value: c.code,
  label: c.name,
  sublabel: c.region ? "Region" : undefined,
});

function CodeTag({ code }: { code: string }) {
  return (
    <span className="inline-flex w-8 shrink-0 justify-center rounded-xs bg-surface-sunken px-1 text-caption font-medium tabular text-text-secondary">
      {code.length > 3 ? "ALL" : code}
    </span>
  );
}

function useCountryOptions(withRegions: boolean, first?: string | null) {
  return useMemo(() => {
    const list = withRegions ? [...REGIONS, ...COUNTRIES] : COUNTRIES;
    const ordered = first
      ? [...list.filter((c) => c.code === first), ...list.filter((c) => c.code !== first)]
      : list;
    const byCode = new Map(ordered.map((c) => [c.code, c]));
    const filter = (options: SearchableOption[], query: string) => {
      if (!query.trim()) return options;
      const allowed = new Set(options.map((o) => o.value));
      return searchCountries(query, ordered)
        .filter((c) => allowed.has(c.code))
        .map(toOption);
    };
    return { options: ordered.map(toOption), byCode, list: ordered, filter };
  }, [withRegions, first]);
}

function NoMatch({ query, list }: { query: string; list: Country[] }) {
  const near = closestCountries(query, list);
  return (
    <p className="px-2.5 py-3 text-caption text-text-subtle">
      No country matches “{query}”.
      {near.length ? ` Try ${near.map((c) => c.name).join(", ")}.` : null}
    </p>
  );
}

export function CountrySelect({
  value,
  onChange,
  disabled,
  first,
  "aria-label": ariaLabel,
}: {
  value: string | null;
  onChange: (code: string | null) => void;
  disabled?: boolean;
  /** A code to list first when nothing is typed, e.g. the registered country. */
  first?: string | null;
  "aria-label"?: string;
}) {
  const { options, list, filter } = useCountryOptions(false, first);
  return (
    <SearchableSelect
      options={options}
      value={value}
      onChange={onChange}
      filter={filter}
      renderNoMatch={(query) => <NoMatch query={query} list={list} />}
      placeholder="Choose a country"
      searchPlaceholder="Type a country"
      disabled={disabled}
      aria-label={ariaLabel}
      renderValue={(option) =>
        option ? (
          <>
            <CodeTag code={option.value} />
            <span className="truncate">{option.label}</span>
          </>
        ) : (
          <span className="text-text-faint">Choose a country</span>
        )
      }
      renderOption={(option) => (
        <span className="flex min-w-0 flex-1 items-center gap-2">
          <CodeTag code={option.value} />
          <span className="truncate">{option.label}</span>
        </span>
      )}
    />
  );
}

export function CountryMultiSelect({
  value,
  onChange,
  withRegions = false,
  disabled,
  first,
  "aria-label": ariaLabel,
}: {
  value: string[];
  onChange: (codes: string[]) => void;
  /** Offer region groups (European Union, Gulf Cooperation Council, Worldwide). */
  withRegions?: boolean;
  disabled?: boolean;
  first?: string | null;
  "aria-label"?: string;
}) {
  const { options, list, filter } = useCountryOptions(withRegions, first);
  const remaining = options.filter((o) => !value.includes(o.value));
  const remove = (code: string) => onChange(value.filter((c) => c !== code));
  return (
    <div className="space-y-2">
      {value.length ? (
        <ul className="flex flex-wrap gap-1.5" aria-label={`${ariaLabel ?? "Countries"} chosen`}>
          {value.map((code) => (
            <li
              key={code}
              className="flex items-center gap-1.5 rounded-sm border border-border bg-surface-primary py-0.5 pl-1 pr-1.5 text-body-sm text-text-primary"
            >
              <CodeTag code={code} />
              {countryName(code)}
              {disabled ? null : (
                <button
                  type="button"
                  onClick={() => remove(code)}
                  aria-label={`Remove ${countryName(code)}`}
                  className="rounded-xs text-text-subtle hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
                >
                  <Icon name="x" className="size-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      <SearchableSelect
        options={remaining}
        value={null}
        onChange={(code) => {
          if (code && !value.includes(code)) onChange([...value, code]);
        }}
        filter={filter}
        keepOpen
        renderNoMatch={(query) => <NoMatch query={query} list={list} />}
        placeholder={value.length ? "Add another" : "Add a country"}
        searchPlaceholder="Type a country"
        disabled={disabled}
        aria-label={ariaLabel}
        renderOption={(option) => (
          <span className="flex min-w-0 flex-1 items-center gap-2">
            <CodeTag code={option.value} />
            <span className="min-w-0 flex-1">
              <span className="block truncate">{option.label}</span>
              {option.sublabel ? (
                <span className="block truncate text-caption text-text-subtle">{option.sublabel}</span>
              ) : null}
            </span>
          </span>
        )}
      />
    </div>
  );
}
