/**
 * Self check for the country search (guided onboarding, part 3 section 12).
 * Run with plain Node, no test runner needed:  node scripts/check-countries.ts
 */
import assert from "node:assert/strict";
import { COUNTRIES, closestCountries, countryName, searchCountries } from "../src/lib/countries.ts";

const first = (query: string) => searchCountries(query)[0]?.code;

assert.equal(COUNTRIES.length, 249);
assert.equal(new Set(COUNTRIES.map((c) => c.code)).size, 249);
assert.equal(countryName("PK"), "Pakistan");
assert.equal(countryName("EU"), "European Union");

const finds: [string, string][] = [
  ["pak", "PK"], ["Pakistan", "PK"], ["uae", "AE"], ["emirates", "AE"], ["ksa", "SA"],
  ["uk", "GB"], ["usa", "US"], ["america", "US"], ["oman", "OM"], ["australia", "AU"],
  ["holland", "NL"], ["czech republic", "CZ"], ["turkey", "TR"], ["cote d ivoire", "CI"],
  // misspellings
  ["Pakstan", "PK"], ["Pakisten", "PK"], ["Saudia Arabia", "SA"], ["Untied States", "US"],
  ["Austrailia", "AU"], ["Omn", "OM"], ["Germnay", "DE"],
];
for (const [query, code] of finds) assert.equal(first(query), code, `"${query}" should find ${code}`);

const ma = searchCountries("ma").map((c) => c.code);
assert.deepEqual(ma.slice(0, 2), ["MA", "MO"], "exact code first, then names starting with it");
assert.ok(ma.indexOf("MY") < ma.indexOf("IM"), "name starts before word starts");

assert.deepEqual(searchCountries("Atlantis"), []);
assert.equal(closestCountries("Atlantis").length, 3);

console.log(`countries: ${finds.length + 6} checks passed`);
