/**
 * Countries for pickers: ISO 3166-1 alpha-2 codes with common English names, aliases,
 * region groups, and a search that forgives spelling mistakes.
 *
 * The backend accepts exactly these 249 codes plus the region codes below
 * (`backend/src/verity/shared/countries.py`). Names and search live only here.
 * Guided onboarding plan, part 3 section 12.
 */

const RAW = `AD Andorra|AE United Arab Emirates;UAE;Emirates;Dubai;Abu Dhabi|AF Afghanistan|AG Antigua and Barbuda|AI Anguilla|AL Albania|AM Armenia|AO Angola|AQ Antarctica|AR Argentina|AS American Samoa|AT Austria;Osterreich|AU Australia;Oz|AW Aruba|AX Aland Islands|AZ Azerbaijan|BA Bosnia and Herzegovina|BB Barbados|BD Bangladesh|BE Belgium|BF Burkina Faso|BG Bulgaria|BH Bahrain|BI Burundi|BJ Benin|BL Saint Barthelemy|BM Bermuda|BN Brunei|BO Bolivia|BQ Caribbean Netherlands;Bonaire|BR Brazil;Brasil|BS Bahamas|BT Bhutan|BV Bouvet Island|BW Botswana|BY Belarus|BZ Belize|CA Canada|CC Cocos Islands|CD Democratic Republic of the Congo;DRC;Congo Kinshasa|CF Central African Republic|CG Republic of the Congo;Congo Brazzaville|CH Switzerland;Schweiz;Suisse|CI Ivory Coast;Cote d'Ivoire|CK Cook Islands|CL Chile|CM Cameroon|CN China;PRC|CO Colombia|CR Costa Rica|CU Cuba|CV Cape Verde;Cabo Verde|CW Curacao|CX Christmas Island|CY Cyprus|CZ Czechia;Czech Republic|DE Germany;Deutschland|DJ Djibouti|DK Denmark|DM Dominica|DO Dominican Republic|DZ Algeria|EC Ecuador|EE Estonia|EG Egypt|EH Western Sahara|ER Eritrea|ES Spain;Espana|ET Ethiopia|FI Finland|FJ Fiji|FK Falkland Islands|FM Micronesia|FO Faroe Islands|FR France|GA Gabon|GB United Kingdom;UK;Britain;Great Britain;England;Scotland;Wales;Northern Ireland|GD Grenada|GE Georgia|GF French Guiana|GG Guernsey|GH Ghana|GI Gibraltar|GL Greenland|GM Gambia|GN Guinea|GP Guadeloupe|GQ Equatorial Guinea|GR Greece;Hellas|GS South Georgia and the South Sandwich Islands|GT Guatemala|GU Guam|GW Guinea-Bissau|GY Guyana|HK Hong Kong|HM Heard Island and McDonald Islands|HN Honduras|HR Croatia;Hrvatska|HT Haiti|HU Hungary|ID Indonesia|IE Ireland;Eire|IL Israel|IM Isle of Man|IN India;Bharat|IO British Indian Ocean Territory|IQ Iraq|IR Iran|IS Iceland|IT Italy;Italia|JE Jersey|JM Jamaica|JO Jordan|JP Japan;Nippon|KE Kenya|KG Kyrgyzstan|KH Cambodia|KI Kiribati|KM Comoros|KN Saint Kitts and Nevis|KP North Korea|KR South Korea;Korea|KW Kuwait|KY Cayman Islands|KZ Kazakhstan|LA Laos|LB Lebanon|LC Saint Lucia|LI Liechtenstein|LK Sri Lanka|LR Liberia|LS Lesotho|LT Lithuania|LU Luxembourg|LV Latvia|LY Libya|MA Morocco|MC Monaco|MD Moldova|ME Montenegro|MF Saint Martin|MG Madagascar|MH Marshall Islands|MK North Macedonia;Macedonia|ML Mali|MM Myanmar;Burma|MN Mongolia|MO Macao;Macau|MP Northern Mariana Islands|MQ Martinique|MR Mauritania|MS Montserrat|MT Malta|MU Mauritius|MV Maldives|MW Malawi|MX Mexico|MY Malaysia|MZ Mozambique|NA Namibia|NC New Caledonia|NE Niger|NF Norfolk Island|NG Nigeria|NI Nicaragua|NL Netherlands;Holland|NO Norway;Norge|NP Nepal|NR Nauru|NU Niue|NZ New Zealand;Aotearoa|OM Oman|PA Panama|PE Peru|PF French Polynesia|PG Papua New Guinea|PH Philippines|PK Pakistan|PL Poland;Polska|PM Saint Pierre and Miquelon|PN Pitcairn Islands|PR Puerto Rico|PS Palestine|PT Portugal|PW Palau|PY Paraguay|QA Qatar|RE Reunion|RO Romania|RS Serbia|RU Russia;Russian Federation|RW Rwanda|SA Saudi Arabia;KSA;Saudi|SB Solomon Islands|SC Seychelles|SD Sudan|SE Sweden;Sverige|SG Singapore|SH Saint Helena|SI Slovenia|SJ Svalbard and Jan Mayen|SK Slovakia|SL Sierra Leone|SM San Marino|SN Senegal|SO Somalia|SR Suriname|SS South Sudan|ST Sao Tome and Principe|SV El Salvador|SX Sint Maarten|SY Syria|SZ Eswatini;Swaziland|TC Turks and Caicos Islands|TD Chad|TF French Southern Territories|TG Togo|TH Thailand|TJ Tajikistan|TK Tokelau|TL Timor-Leste;East Timor|TM Turkmenistan|TN Tunisia|TO Tonga|TR Turkiye;Turkey|TT Trinidad and Tobago|TV Tuvalu|TW Taiwan|TZ Tanzania|UA Ukraine|UG Uganda|UM United States Minor Outlying Islands|US United States;USA;US;America;United States of America|UY Uruguay|UZ Uzbekistan|VA Vatican City;Holy See|VC Saint Vincent and the Grenadines|VE Venezuela|VG British Virgin Islands|VI US Virgin Islands|VN Vietnam;Viet Nam|VU Vanuatu|WF Wallis and Futuna|WS Samoa|YE Yemen|YT Mayotte|ZA South Africa|ZM Zambia|ZW Zimbabwe`;

export type Country = {
  code: string;
  name: string;
  aliases: string[];
  /** A region group (EU, GCC...) rather than a country. */
  region?: boolean;
};

export const COUNTRIES: Country[] = RAW.split("|").map((entry) => {
  const code = entry.slice(0, 2);
  const [name, ...aliases] = entry.slice(3).split(";");
  return { code, name: name ?? code, aliases };
});

/** Region groups the backend also accepts (customers and data location questions). */
export const REGIONS: Country[] = [
  { code: "EU", name: "European Union", aliases: ["EU", "Europe"], region: true },
  { code: "EEA", name: "European Economic Area", aliases: ["EEA"], region: true },
  { code: "GCC", name: "Gulf Cooperation Council", aliases: ["GCC", "Gulf"], region: true },
  { code: "WORLD", name: "Worldwide", aliases: ["Global", "Everywhere"], region: true },
];

const BY_CODE = new Map([...COUNTRIES, ...REGIONS].map((c) => [c.code, c]));

export function countryName(code: string): string {
  return BY_CODE.get(code)?.name ?? code;
}

/** Lower case, accents removed, punctuation to spaces. */
function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Damerau-Levenshtein distance (with adjacent swaps), stopped early past `limit`. */
export function editDistance(a: string, b: string, limit = 3): number {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  const rows = a.length + 1;
  const cols = b.length + 1;
  const d: number[][] = Array.from({ length: rows }, (_, i) =>
    Array.from({ length: cols }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  );
  for (let i = 1; i < rows; i += 1) {
    let rowMin = Number.POSITIVE_INFINITY;
    for (let j = 1; j < cols; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let value = Math.min(
        (d[i - 1]?.[j] ?? 0) + 1,
        (d[i]?.[j - 1] ?? 0) + 1,
        (d[i - 1]?.[j - 1] ?? 0) + cost,
      );
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        value = Math.min(value, (d[i - 2]?.[j - 2] ?? 0) + 1);
      }
      const row = d[i];
      if (row) row[j] = value;
      rowMin = Math.min(rowMin, value);
    }
    if (rowMin > limit) return limit + 1;
  }
  return d[a.length]?.[b.length] ?? limit + 1;
}

function allowedTypos(query: string): number {
  return query.length <= 5 ? 1 : 2;
}

/**
 * Rank countries for what was typed. Order of preference: the name starts with it, a word
 * of the name starts with it, an alias or the code matches, the name contains it, then a
 * spelling match (one mistake for up to five letters, two for longer).
 */
export function searchCountries(query: string, list: Country[] = COUNTRIES): Country[] {
  const q = fold(query);
  if (!q) return list;
  const scored: { country: Country; score: number }[] = [];
  for (const country of list) {
    const name = fold(country.name);
    const aliases = country.aliases.map(fold);
    let score: number | null = null;
    // An exact code or alias wins outright: "uk" is the United Kingdom before Ukraine,
    // "america" the United States before American Samoa.
    if (fold(country.code) === q || aliases.includes(q)) score = -1;
    else if (name.startsWith(q)) score = 0;
    else if (name.split(" ").some((word) => word.startsWith(q))) score = 1;
    else if (fold(country.code) === q || aliases.some((a) => a === q || a.startsWith(q))) score = 2;
    else if (name.includes(q) || aliases.some((a) => a.includes(q))) score = 3;
    else {
      // A misspelt whole name ranks before a misspelt start of a longer one: "Omn" is Oman,
      // not Monaco.
      const limit = allowedTypos(q);
      const candidates = [name, ...aliases, ...name.split(" ")];
      const whole = Math.min(...candidates.map((c) => editDistance(q, c, limit)));
      const start = Math.min(...candidates.map((c) => editDistance(q, c.slice(0, q.length), limit)));
      if (whole <= limit) score = 4 + whole;
      else if (start <= limit) score = 7 + start;
    }
    if (score !== null) scored.push({ country, score });
  }
  return scored
    .sort((x, y) => x.score - y.score || x.country.name.localeCompare(y.country.name))
    .map((s) => s.country);
}

/** The three closest names, for "Did you mean" when nothing matched. */
export function closestCountries(query: string, list: Country[] = COUNTRIES): Country[] {
  const q = fold(query);
  if (!q) return [];
  return list
    .map((country) => ({ country, distance: editDistance(q, fold(country.name), 99) }))
    .sort((x, y) => x.distance - y.distance)
    .slice(0, 3)
    .map((s) => s.country);
}
