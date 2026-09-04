/**
 * Minimal reader for the OOXML formats the server accepts: xlsx and pptx.
 *
 * Both are ZIP archives of XML, and the browser can already do both halves —
 * `DecompressionStream` inflates, `DOMParser` parses. So we read them here
 * rather than taking a dependency: the only maintained JS spreadsheet parser,
 * SheetJS, ships on npm frozen at 0.18.5, which carries CVE-2023-30533
 * (prototype pollution) and CVE-2024-22363 (ReDoS). Neither is a thing to
 * point at untrusted uploaded bytes in a compliance product.
 *
 * What this deliberately does NOT do: styling, merged cells, charts, images,
 * formulas (the cached value is shown, which is what Excel last computed),
 * or ZIP64 (irrelevant under the 25 MB upload cap). It reads the values, which
 * is what a preview is for. Anything richer, download the original.
 */

const LOCAL_HEADER = 0x04034b50;
const CENTRAL_ENTRY = 0x02014b50;
const EOCD = 0x06054b50;

/** True when this browser can inflate. Every current engine can; a refusal
 *  falls back to the download prompt rather than showing an error. */
export function canReadOoxml(): boolean {
  return typeof DecompressionStream !== "undefined";
}

async function inflate(bytes: Uint8Array, method: number): Promise<Uint8Array> {
  if (method === 0) return bytes; // STORED — small files are often not deflated
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(
    new DecompressionStream("deflate-raw"),
  );
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

/**
 * Every entry in the archive, by path.
 *
 * Read via the central directory at the end of the file rather than by walking
 * local headers: a streamed ZIP puts its sizes in a trailing data descriptor,
 * so the local header's size fields can be zero, while the central directory
 * is always authoritative.
 */
async function unzip(blob: Blob): Promise<Map<string, Uint8Array>> {
  const buffer = new Uint8Array(await blob.arrayBuffer());
  const view = new DataView(buffer.buffer);

  // The end-of-central-directory record sits in the last 64 KB (its own 22
  // bytes plus up to 65535 of archive comment).
  let eocd = -1;
  for (let i = buffer.length - 22; i >= Math.max(0, buffer.length - 65557); i -= 1) {
    if (view.getUint32(i, true) === EOCD) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) throw new Error("not a zip archive");

  const count = view.getUint16(eocd + 10, true);
  let cursor = view.getUint32(eocd + 16, true);
  const decoder = new TextDecoder();
  const files = new Map<string, Uint8Array>();

  for (let i = 0; i < count; i += 1) {
    if (view.getUint32(cursor, true) !== CENTRAL_ENTRY) break;
    const method = view.getUint16(cursor + 10, true);
    const compressedSize = view.getUint32(cursor + 20, true);
    const nameLength = view.getUint16(cursor + 28, true);
    const extraLength = view.getUint16(cursor + 30, true);
    const commentLength = view.getUint16(cursor + 32, true);
    const localOffset = view.getUint32(cursor + 42, true);
    const name = decoder.decode(buffer.subarray(cursor + 46, cursor + 46 + nameLength));

    if (view.getUint32(localOffset, true) === LOCAL_HEADER) {
      // The local header's own name/extra lengths, not the central entry's —
      // the extra field routinely differs between the two.
      const localName = view.getUint16(localOffset + 26, true);
      const localExtra = view.getUint16(localOffset + 28, true);
      const start = localOffset + 30 + localName + localExtra;
      files.set(name, await inflate(buffer.subarray(start, start + compressedSize), method));
    }
    cursor += 46 + nameLength + extraLength + commentLength;
  }
  return files;
}

function parseXml(bytes: Uint8Array | undefined): Document | null {
  if (!bytes) return null;
  const doc = new DOMParser().parseFromString(new TextDecoder().decode(bytes), "application/xml");
  return doc.querySelector("parsererror") ? null : doc;
}

/** "BC12" -> 54. Rows are sparse, so a cell's column comes from its reference. */
function columnIndex(ref: string): number {
  let n = 0;
  for (const char of ref) {
    const code = char.charCodeAt(0);
    if (code < 65 || code > 90) break;
    n = n * 26 + (code - 64);
  }
  return n - 1;
}

/** Excel counts days from 1899-12-30 — 1900 is treated as a leap year, which
 *  it was not, and the epoch is shifted to absorb it. */
function serialToDate(serial: number): string {
  const ms = Math.round((serial - 25569) * 86_400_000);
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return String(serial);
  return serial % 1 === 0
    ? date.toISOString().slice(0, 10)
    : date.toISOString().slice(0, 16).replace("T", " ");
}

/** Built-in numFmt ids that mean a date or a time. */
const DATE_FORMAT_IDS = new Set([14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47]);

/** Which cell styles resolve to a date format, so 45678 renders as a date
 *  rather than as the number nobody can read. */
function dateStyles(files: Map<string, Uint8Array>): Set<number> {
  const doc = parseXml(files.get("xl/styles.xml"));
  const out = new Set<number>();
  if (!doc) return out;

  const custom = new Set<number>();
  for (const fmt of doc.getElementsByTagName("numFmt")) {
    const code = fmt.getAttribute("formatCode") ?? "";
    // A date format has y/m/d outside of literal quotes; a currency does not.
    if (/[ymd]/i.test(code.replace(/"[^"]*"/g, "")) && !/^[^ymd]*$/i.test(code)) {
      custom.add(Number(fmt.getAttribute("numFmtId")));
    }
  }
  const xfs = doc.getElementsByTagName("cellXfs")[0];
  if (!xfs) return out;
  [...xfs.getElementsByTagName("xf")].forEach((xf, index) => {
    const id = Number(xf.getAttribute("numFmtId") ?? 0);
    if (DATE_FORMAT_IDS.has(id) || custom.has(id)) out.add(index);
  });
  return out;
}

/** A row keeps the index the workbook gave it. A sparse sheet skips numbers,
 *  so counting rendered rows would mislabel every row after the first gap. */
export type SheetRow = { index: number; cells: string[] };
export type Sheet = { name: string; rows: SheetRow[] };

/** Every sheet in a workbook, in the order the workbook lists them. */
export async function readWorkbook(blob: Blob, maxRows = 500): Promise<Sheet[]> {
  const files = await unzip(blob);

  // Shared strings: most text cells are an index into this table.
  const sharedDoc = parseXml(files.get("xl/sharedStrings.xml"));
  const shared = sharedDoc
    ? [...sharedDoc.getElementsByTagName("si")].map((si) =>
        [...si.getElementsByTagName("t")].map((t) => t.textContent ?? "").join(""),
      )
    : [];

  // rId -> worksheet path.
  const relsDoc = parseXml(files.get("xl/_rels/workbook.xml.rels"));
  const rels = new Map<string, string>();
  if (relsDoc) {
    for (const rel of relsDoc.getElementsByTagName("Relationship")) {
      const target = rel.getAttribute("Target") ?? "";
      rels.set(rel.getAttribute("Id") ?? "", target.replace(/^\/?(xl\/)?/, "xl/"));
    }
  }

  const bookDoc = parseXml(files.get("xl/workbook.xml"));
  if (!bookDoc) throw new Error("no workbook");
  const styles = dateStyles(files);
  const sheets: Sheet[] = [];

  for (const entry of bookDoc.getElementsByTagName("sheet")) {
    const name = entry.getAttribute("name") ?? "Sheet";
    const id =
      entry.getAttribute("r:id") ?? entry.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id") ?? "";
    const sheetDoc = parseXml(files.get(rels.get(id) ?? ""));
    if (!sheetDoc) continue;

    const rows: SheetRow[] = [];
    for (const row of sheetDoc.getElementsByTagName("row")) {
      if (rows.length >= maxRows) break;
      const index = Number(row.getAttribute("r") ?? rows.length + 1);
      const cells: string[] = [];
      for (const cell of row.getElementsByTagName("c")) {
        const at = columnIndex(cell.getAttribute("r") ?? "A");
        const type = cell.getAttribute("t");
        let text: string;
        if (type === "s") {
          text = shared[Number(cell.getElementsByTagName("v")[0]?.textContent ?? -1)] ?? "";
        } else if (type === "inlineStr") {
          text = [...cell.getElementsByTagName("t")].map((t) => t.textContent ?? "").join("");
        } else {
          const raw = cell.getElementsByTagName("v")[0]?.textContent ?? "";
          const style = Number(cell.getAttribute("s") ?? -1);
          text = raw !== "" && styles.has(style) && !Number.isNaN(Number(raw))
            ? serialToDate(Number(raw))
            : raw;
        }
        while (cells.length < at) cells.push("");
        cells[at] = text;
      }
      rows.push({ index, cells });
    }
    sheets.push({ name, rows });
  }
  return sheets;
}

export type Slide = { name: string; lines: string[] };

/** The text of each slide, in slide order. A deck's substance is its words;
 *  the layout is not something a preview pane can honestly reproduce. */
export async function readSlides(blob: Blob): Promise<Slide[]> {
  const files = await unzip(blob);
  const paths = [...files.keys()]
    .filter((p) => /^ppt\/slides\/slide\d+\.xml$/.test(p))
    .sort((a, b) => {
      const n = (p: string) => Number(p.match(/(\d+)\.xml$/)?.[1] ?? 0);
      return n(a) - n(b);
    });

  return paths.map((path, index) => {
    const doc = parseXml(files.get(path));
    const lines = doc
      ? [...doc.getElementsByTagName("a:t")].map((t) => t.textContent ?? "").filter(Boolean)
      : [];
    return { name: `Slide ${index + 1}`, lines };
  });
}
