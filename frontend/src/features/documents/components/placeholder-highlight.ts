import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

/**
 * Highlights the `{{fields}}` a policy still needs someone to decide.
 *
 * A shipped template says things like "access reviews are performed on a
 * {{frequency}} basis". That is not prose to skim past — it is a decision the
 * customer has to make and then live up to, and publishing it unfilled puts a
 * placeholder in front of an auditor.
 *
 * Implemented as decorations rather than by rewriting the document: the content
 * is untouched, so a placeholder stays exactly what it is until a person types
 * over it, and nothing is added to the saved HTML. Decorations also survive
 * undo/redo for free, because they are derived from the document rather than
 * being part of it.
 */

export const placeholderHighlightKey = new PluginKey("placeholderHighlight");

/** Must match the backend's `placeholders.PLACEHOLDER`, or the editor and the
 *  document's own count disagree about what is outstanding. */
const PATTERN = /\{\{\s*([a-z0-9_]+)\s*\}\}/gi;

function decorate(doc: ProseMirrorNode): DecorationSet {
  const decorations: Decoration[] = [];

  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return;
    PATTERN.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = PATTERN.exec(node.text)) !== null) {
      const from = pos + match.index;
      decorations.push(
        Decoration.inline(from, from + match[0].length, {
          class: "policy-placeholder",
          // Read out by a screen reader, and shown as a tooltip: the highlight
          // alone does not say why it is highlighted.
          title: `${match[1].replace(/_/g, " ")}: replace this before publishing`,
          "data-placeholder": match[1].toLowerCase(),
        }),
      );
    }
  });

  return DecorationSet.create(doc, decorations);
}

export const PlaceholderHighlight = Extension.create({
  name: "placeholderHighlight",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: placeholderHighlightKey,
        state: {
          init: (_config, state) => decorate(state.doc),
          // Recompute only when the text actually changed. Selection moves fire
          // transactions constantly and re-scanning a 5,000-word policy on each
          // one is wasted work.
          apply: (tr, old) => (tr.docChanged ? decorate(tr.doc) : old),
        },
        props: {
          decorations(state) {
            return placeholderHighlightKey.getState(state) as DecorationSet | undefined;
          },
        },
      }),
    ];
  },
});
