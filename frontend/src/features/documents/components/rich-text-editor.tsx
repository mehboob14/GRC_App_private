import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { TextStyle, Color, FontFamily } from "@tiptap/extension-text-style";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { useRef } from "react";
import { Icon } from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { cn } from "@/lib/cn";
import "../document-prose.css";

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

function ToolbarButton({
  icon,
  label,
  active,
  disabled,
  onClick,
}: {
  icon?: IconName;
  label?: string;
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
      title={label}
      className={cn(
        "flex h-8 min-w-8 items-center justify-center gap-1 rounded-xs px-1.5 text-body-sm",
        active
          ? "bg-action-accent-tint text-text-link"
          : "text-text-secondary hover:bg-surface-hover",
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent",
      )}
    >
      {icon ? <Icon name={icon} className="size-4" /> : null}
      {label && !icon ? <span className="font-medium">{label}</span> : null}
    </button>
  );
}

function Divider() {
  return <span className="mx-1 h-5 w-px bg-border" />;
}

function Toolbar({ editor }: { editor: Editor }) {
  const imageInput = useRef<HTMLInputElement | null>(null);

  function addImage(file: File) {
    // No object storage yet (Stage 5) — inline the image as a data URL so it
    // travels with the HTML. The real editor uploads and inserts a URL.
    const reader = new FileReader();
    reader.onload = () => {
      editor.chain().focus().setImage({ src: String(reader.result) }).run();
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center gap-0.5 border-b border-border bg-surface-primary px-2 py-1.5">
      <ToolbarButton icon="undo" label="Undo" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} />
      <ToolbarButton icon="redo" label="Redo" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} />
      <Divider />
      <ToolbarButton label="H1" active={editor.isActive("heading", { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} />
      <ToolbarButton label="H2" active={editor.isActive("heading", { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} />
      <ToolbarButton label="H3" active={editor.isActive("heading", { level: 3 })} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} />
      <Divider />
      <ToolbarButton icon="bold" label="Bold" active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()} />
      <ToolbarButton icon="italic" label="Italic" active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()} />
      <ToolbarButton icon="strike" label="Strikethrough" active={editor.isActive("strike")} onClick={() => editor.chain().focus().toggleStrike().run()} />
      <Divider />
      <ToolbarButton icon="list" label="Bullet list" active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()} />
      <ToolbarButton icon="listOrdered" label="Numbered list" active={editor.isActive("orderedList")} onClick={() => editor.chain().focus().toggleOrderedList().run()} />
      <ToolbarButton icon="quote" label="Quote" active={editor.isActive("blockquote")} onClick={() => editor.chain().focus().toggleBlockquote().run()} />
      <Divider />

      {/* Text colour */}
      <label className="flex h-8 items-center gap-1 rounded-xs px-1.5 text-text-secondary hover:bg-surface-hover" title="Text colour">
        <Icon name="palette" className="size-4" />
        <select
          className="cursor-pointer bg-transparent text-body-sm outline-none"
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

      {/* Font family */}
      <label className="flex h-8 items-center gap-1 rounded-xs px-1.5 text-text-secondary hover:bg-surface-hover" title="Font">
        <Icon name="type" className="size-4" />
        <select
          className="cursor-pointer bg-transparent text-body-sm outline-none"
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
      <Divider />

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

/**
 * TipTap rich-text editor storing HTML (ADR-0012). Toolbar covers the controls
 * the client design shows: headings, lists, bold/italic/strike, text colour,
 * quote, fonts, links, image insert, undo/redo.
 */
export function RichTextEditor({
  content,
  onChange,
}: {
  content: string;
  onChange: (html: string) => void;
}) {
  const editor = useEditor({
    extensions: [
      StarterKit,
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
        class:
          "prose-doc w-full min-h-[60vh] px-10 py-8 outline-none",
      },
    },
  });

  if (!editor) return null;

  return (
    <div className="flex h-full flex-col">
      <Toolbar editor={editor} />
      <div className="min-h-0 flex-1 overflow-y-auto bg-surface-sunken">
        <div className="mx-auto my-6 max-w-[860px] rounded-lg border border-border bg-surface-primary shadow-1">
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
}
