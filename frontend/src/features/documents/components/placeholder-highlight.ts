import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { findPlaceholderMarks, MARK_META } from "../placeholder-marks";

/**
 * Highlights what a policy still needs someone to fill in, one colour per kind:
 * `{{fields}}` to decide, `<written prompts>` to replace, `[Optional]` text to
 * keep or cut, and the company name the platform filled in.
 *
 * A shipped template says things like "access reviews are performed on a
 * {{frequency}} basis". That is not prose to skim past: it is a decision the
 * customer has to make and then live up to, and publishing it unfilled puts a
 * placeholder in front of an auditor.
 *
 * Implemented as decorations rather than by rewriting the document: the content
 * is untouched, nothing is added to the saved HTML, and the highlights survive
 * undo and redo because they are derived from the document.
 */

export const placeholderHighlightKey = new PluginKey("placeholderHighlight");

function decorate(doc: ProseMirrorNode, companyNames: readonly string[]): DecorationSet {
  const decorations: Decoration[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return;
    for (const mark of findPlaceholderMarks(node.text, companyNames)) {
      decorations.push(
        Decoration.inline(pos + mark.from, pos + mark.to, {
          class: MARK_META[mark.kind].className,
          // Read out by a screen reader and shown on hover: the colour alone
          // does not say why the text is highlighted.
          title: MARK_META[mark.kind].hint(mark.label),
          "data-placeholder": mark.key,
        }),
      );
    }
  });
  return DecorationSet.create(doc, decorations);
}

export const PlaceholderHighlight = Extension.create<{ companyNames: string[] }>({
  name: "placeholderHighlight",

  addOptions() {
    return { companyNames: [] };
  },

  addProseMirrorPlugins() {
    const { companyNames } = this.options;
    return [
      new Plugin({
        key: placeholderHighlightKey,
        state: {
          init: (_config, state) => decorate(state.doc, companyNames),
          // Recompute only when the text actually changed. Selection moves fire
          // transactions constantly and re-scanning a 5,000-word policy on each
          // one is wasted work.
          apply: (tr, old) => (tr.docChanged ? decorate(tr.doc, companyNames) : old),
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
