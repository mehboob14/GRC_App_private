import { useEditor, useEditorState, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { TextStyle, Color, FontFamily } from "@tiptap/extension-text-style";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { PlaceholderHighlight } from "./placeholder-highlight";
import { useRef, type ReactNode } from "react";
import { Icon } from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { cn } from "@/lib/cn";
import "@/styles/document-prose.css";

const FONTS = [
  { label: "Default", value: "" },
  { label: "Sans", value: "system-ui, sans-serif" },
  { label: "Serif", value: "Georgia, 'Times New Roman', serif" },
  { label: "Mono", value: "'JetBrains Mono', ui-monospace, monospace" },
];

const COLORS = [
  { label: "Default", value: "" },
  { label: "Red", value: "#DC2626" },
  { label: "Amber", value: "#CA8A04" },
  { label: "Green", value: "#16A34A" },
  { label: "Blue", value: "#2563EB" },
  { label: "Ink", value: "#111827" },
];

/** Must match the backend's `placeholders.PLACEHOLDER`. */
const PLACEHOLDER = /\{\{\s*([a-z0-9_]+)\s*\}\}/gi;

function ToolbarButton({
  icon,
  label,
  text,
  active,
  disabled,
  onClick,
}: {
  icon?: IconName;
  label: string;
  /** A short visible label instead of an icon, e.g. "H1". */
  text?: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={label}
      title={label}
      className={cn(
        "flex h-8 min-w-8 items-center justify-center rounded-sm px-1.5 text-body-sm transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-action-accent",
        active
          ? "bg-surface-primary text-action-accent shadow-1"
          : "text-text-secondary hover:bg-surface-primary hover:text-text-primary",
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent",
      )}
    >
      {icon ? <Icon name={icon} className="size-4" /> : null}
      {text ? <span className="font-semibold">{text}</span> : null}
    </button>
  );
}

/** A set of related controls on one filled track, instead of divider lines. */
function Group({ children }: { children: ReactNode }) {
  return <div className="flex items-center gap-0.5 rounded-md bg-surface-sunken p-0.5">{children}</div>;
}

function Toolbar({ editor }: { editor: Editor }) {
  const imageInput = useRef<HTMLInputElement | null>(null);

  function addImage(file: File) {
    // No object storage yet: inline the image as a data URL so it travels with
    // the HTML. The real editor uploads and inserts a URL.
    const reader = new FileReader();
    reader.onload = () => {
      editor.chain().focus().setImage({ src: String(reader.result) }).run();
    };
    reader.readAsDataURL(file);
  }

  const selectClass =
    "h-8 cursor-pointer rounded-sm bg-transparent pl-1 pr-1 text-body-sm text-text-secondary outline-none hover:bg-surface-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent";

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border bg-surface-primary px-5 py-2">
      <Group>
        <ToolbarButton icon="undo" label="Undo" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} />
        <ToolbarButton icon="redo" label="Redo" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} />
      </Group>
      <Group>
        <ToolbarButton text="H1" label="Heading 1" active={editor.isActive("heading", { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} />
        <ToolbarButton text="H2" label="Heading 2" active={editor.isActive("heading", { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} />
        <ToolbarButton text="H3" label="Heading 3" active={editor.isActive("heading", { level: 3 })} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} />
      </Group>
      <Group>
        <ToolbarButton icon="bold" label="Bold" active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()} />
        <ToolbarButton icon="italic" label="Italic" active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()} />
        <ToolbarButton icon="strike" label="Strikethrough" active={editor.isActive("strike")} onClick={() => editor.chain().focus().toggleStrike().run()} />
      </Group>
      <Group>
        <ToolbarButton icon="list" label="Bullet list" active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()} />
        <ToolbarButton icon="listOrdered" label="Numbered list" active={editor.isActive("orderedList")} onClick={() => editor.chain().focus().toggleOrderedList().run()} />
        <ToolbarButton icon="quote" label="Quote" active={editor.isActive("blockquote")} onClick={() => editor.chain().focus().toggleBlockquote().run()} />
      </Group>
      <Group>
        <label className="flex items-center gap-1 pl-1.5 text-text-secondary" title="Text colour">
          <Icon name="palette" className="size-4" />
          <select
            aria-label="Text colour"
            className={selectClass}
            value={editor.getAttributes("textStyle").color ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              if (v) editor.chain().focus().setColor(v).run();
              else editor.chain().focus().unsetColor().run();
            }}
          >
            {COLORS.map((c) => (
              <option key={c.label} value={c.value}>{c.label}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1 pl-1.5 text-text-secondary" title="Font">
          <Icon name="type" className="size-4" />
          <select
            aria-label="Font"
            className={selectClass}
            value={editor.getAttributes("textStyle").fontFamily ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              if (v) editor.chain().focus().setFontFamily(v).run();
              else editor.chain().focus().unsetFontFamily().run();
            }}
          >
            {FONTS.map((f) => (
              <option key={f.label} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>
      </Group>
      <Group>
        <ToolbarButton
          icon="link"
          label="Link"
          active={editor.isActive("link")}
          onClick={() => {
            const prev = editor.getAttributes("link").href as string | undefined;
            const url = window.prompt("Link URL", prev ?? "https://");
            if (url === null) return;
            if (url === "") editor.chain().focus().unsetLink().run();
            else editor.chain().focus().setLink({ href: url }).run();
          }}
        />
        <ToolbarButton icon="image" label="Insert image" onClick={() => imageInput.current?.click()} />
      </Group>
      <input
        ref={imageInput}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) addImage(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}

type OutlineItem = { pos: number; level: number; text: string };
type PlaceholderGroup = { key: string; ranges: { from: number; to: number }[] };

function humanize(key: string): string {
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * The editor's left panel: what is still to be decided, then the outline.
 *
 * Clicking a placeholder selects its next occurrence, so the reader types
 * straight over `{{frequency}}`; clicking a heading scrolls to it. Both are read
 * from the document on every change, so they never disagree with the page.
 */
function EditorSidebar({ editor, labels }: { editor: Editor; labels: Record<string, string> }) {
  const { outline, placeholders, cursor } = useEditorState({
    editor,
    selector: ({ editor: ed }) => {
      const headings: OutlineItem[] = [];
      const found = new Map<string, { from: number; to: number }[]>();
      ed.state.doc.descendants((node, pos) => {
        if (node.type.name === "heading") {
          headings.push({ pos, level: Number(node.attrs.level) || 1, text: node.textContent });
        }
        if (node.isText && node.text) {
          PLACEHOLDER.lastIndex = 0;
          let match: RegExpExecArray | null;
          while ((match = PLACEHOLDER.exec(node.text)) !== null) {
            const key = match[1].toLowerCase();
            const from = pos + match.index;
            found.set(key, [...(found.get(key) ?? []), { from, to: from + match[0].length }]);
          }
        }
      });
      const groups: PlaceholderGroup[] = [...found.entries()].map(([key, ranges]) => ({ key, ranges }));
      return { outline: headings, placeholders: groups, cursor: ed.state.selection.from };
    },
  });

  const reveal = (from: number, to?: number) => {
    editor
      .chain()
      .focus(undefined, { scrollIntoView: false })
      .setTextSelection(to === undefined ? from : { from, to })
      .run();
    // Centre the exact position, not its paragraph: policy paragraphs run long
    // enough that centring the block can leave the placeholder off screen. The
    // editor focuses on the next frame, so the scroll waits for it.
    requestAnimationFrame(() => {
      const container = editor.view.dom.closest<HTMLElement>("[data-editor-scroll]");
      if (!container) return;
      const coords = editor.view.coordsAtPos(from);
      const box = container.getBoundingClientRect();
      container.scrollBy({ top: coords.top - box.top - box.height / 2, behavior: "smooth" });
    });
  };

  const total = placeholders.reduce((n, p) => n + p.ranges.length, 0);
  const activeHeading = [...outline].reverse().find((h) => h.pos <= cursor)?.pos;

  return (
    <aside className="hidden min-h-0 flex-col overflow-y-auto border-r border-border bg-surface-primary lg:flex">
      <section className="border-b border-border p-4">
        <p className="flex items-center justify-between">
          <span className="type-overline">To decide</span>
          {total > 0 ? (
            <span className="tabular rounded-full bg-status-warning-bg px-2 py-0.5 text-caption font-bold text-status-warning-text">
              {total}
            </span>
          ) : null}
        </p>
        {placeholders.length === 0 ? (
          <p className="mt-2 flex items-center gap-2 text-body-sm text-status-success-text">
            <Icon name="check" className="size-4" />
            Nothing left to decide
          </p>
        ) : (
          <ul className="-mx-2 mt-2 space-y-px">
            {placeholders.map((group) => (
              <li key={group.key}>
                <button
                  type="button"
                  onClick={() => {
                    const next = group.ranges.find((r) => r.from > cursor) ?? group.ranges[0];
                    reveal(next.from, next.to);
                  }}
                  className="flex w-full items-center gap-2.5 rounded-sm px-2 py-1.5 text-left transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
                >
                  <span className="size-2 shrink-0 rounded-full bg-status-warning-base" aria-hidden />
                  <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">
                    {labels[group.key] ?? humanize(group.key)}
                  </span>
                  <span className="tabular text-caption text-text-subtle">{group.ranges.length}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="p-4">
        <p className="type-overline">Outline</p>
        {outline.length === 0 ? (
          <p className="mt-2 text-caption text-text-subtle">Headings appear here.</p>
        ) : (
          <ul className="-mx-2 mt-2 space-y-px">
            {outline.map((heading) => (
              <li key={heading.pos}>
                <button
                  type="button"
                  onClick={() => reveal(heading.pos + 1)}
                  className={cn(
                    "block w-full truncate rounded-sm py-1.5 pr-2 text-left text-body-sm transition-colors duration-80 ease-state",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent",
                    heading.level <= 1 ? "pl-2 font-semibold" : heading.level === 2 ? "pl-2" : "pl-6",
                    heading.pos === activeHeading
                      ? "bg-action-accent-tint text-action-accent"
                      : "text-text-secondary hover:bg-surface-hover hover:text-text-primary",
                  )}
                >
                  {heading.text || "Untitled heading"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}

/**
 * TipTap rich-text editor storing HTML (ADR-0012): the toolbar across the top,
 * what is left to decide and the outline on the left, the page on the right.
 */
export function RichTextEditor({
  content,
  onChange,
  placeholderLabels = {},
}: {
  content: string;
  onChange: (html: string) => void;
  /** Friendly names for `{{placeholder}}` keys, from the document. */
  placeholderLabels?: Record<string, string>;
}) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      // Marks the {{fields}} still to be decided. Decorations only: the saved
      // HTML is untouched.
      PlaceholderHighlight,
      TextStyle,
      Color,
      FontFamily,
      Image.configure({ inline: false, allowBase64: true }),
      Link.configure({ openOnClick: false, autolink: true }),
      Placeholder.configure({ placeholder: "Write the policy…" }),
    ],
    content,
    onUpdate: ({ editor: ed }) => onChange(ed.getHTML()),
    editorProps: {
      attributes: {
        class: "prose-doc w-full min-h-[60vh] px-12 py-10 outline-none",
      },
    },
  });

  if (!editor) return null;

  return (
    <div className="flex h-full flex-col">
      <Toolbar editor={editor} />
      <div className="grid min-h-0 flex-1 lg:grid-cols-[17rem_minmax(0,1fr)]">
        <EditorSidebar editor={editor} labels={placeholderLabels} />
        <div data-editor-scroll className="min-h-0 overflow-y-auto bg-surface-sunken">
          <div className="mx-auto my-8 max-w-[860px] rounded-lg border border-border bg-surface-primary shadow-1">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  );
}
