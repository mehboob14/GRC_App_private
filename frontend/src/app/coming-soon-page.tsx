import { EmptyState } from "@/components/ui";

export function ComingSoonPage({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <EmptyState
      comingSoon
      title={title}
      description={
        description ??
        "This module ships in a later Phase 1 deliverable. Navigation is shown for orientation only."
      }
    />
  );
}
