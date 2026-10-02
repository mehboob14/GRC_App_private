import Image from "next/image";
import Markdown from "react-markdown";
import rehypeSlug from "rehype-slug";
import remarkGfm from "remark-gfm";
import type { GuidePage } from "@/lib/guide";
import { imageInfo, resolveGuideHref } from "@/lib/guide";

export function GuideMarkdown({ page }: { page: GuidePage }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSlug]}
      components={{
        a({ href = "", children }) {
          const target = resolveGuideHref(page, href);
          const external = target.startsWith("https://");
          return <a href={target} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>{children}</a>;
        },
        img({ src = "", alt = "" }) {
          if (typeof src !== "string") throw new Error(`${page.filename}: unsupported image source`);
          const { src: imageSrc, width, height } = imageInfo(src.replace(/^images\//, ""));
          return <a className="guide-image-link" href={imageSrc} target="_blank" rel="noopener noreferrer" aria-label={`Open full-size image: ${alt}`}><Image src={imageSrc} alt={alt} width={width} height={height} unoptimized /></a>;
        },
      }}
    >{page.markdown}</Markdown>
  );
}
