import { Link, useParams } from "react-router-dom";
import { Button, EmptyState } from "@/components/ui";

function humanize(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function ComingSoonPage({
  title,
  description,
  notFound = false,
}: {
  title: string;
  description?: string;
  /** Unknown route — offer the way back instead of a coming-soon promise. */
  notFound?: boolean;
}) {
  const { slug } = useParams();
  const heading = slug ? humanize(slug) : title;

  return (
    <div className="mx-auto max-w-[840px]">
      <h1 className="font-display text-heading-lg text-text-primary">
        {heading}
      </h1>
      <EmptyState
        className="mt-5"
        comingSoon={!notFound}
        title={notFound ? "Nothing lives at this address" : "Ships in a later phase"}
        description={
          description ??
          "This module ships in a later Phase 1 deliverable. Navigation is shown for orientation only."
        }
        action={
          notFound ? (
            <Button asChild>
              <Link to="/quick-start">Back to dashboard</Link>
            </Button>
          ) : undefined
        }
      />
    </div>
  );
}
