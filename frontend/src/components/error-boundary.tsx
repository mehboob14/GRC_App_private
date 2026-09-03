import { Component, type ErrorInfo, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";

/**
 * The app had no error boundary at all, so any render-time exception unmounted
 * the whole tree and left a blank white page with nothing to click.
 *
 * This catches those, keeps the shell usable, and gives the reader a way out.
 * It does NOT catch async failures: a rejected fetch inside react-query never
 * reaches a boundary, and is handled by the view's own error state instead.
 */
type Props = { children: ReactNode; resetKey: string };
type State = { error: Error | null };

class ErrorBoundaryInner extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prev: Props) {
    // Navigating away is the reader's attempt to escape. Honour it, or they are
    // trapped on the error screen for the rest of the session.
    if (this.state.error && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Nothing ships logs off the box today, so the console is the only record.
    console.error("Unhandled render error", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        role="alert"
        className="flex min-h-[60vh] w-full flex-col items-center justify-center px-6 text-center"
      >
        <span className="mb-4 flex size-11 items-center justify-center rounded-md bg-status-danger-bg">
          <Icon name="alert" className="size-5 text-status-danger-base" aria-hidden />
        </span>
        <h1 className="font-display text-heading-md text-text-primary">
          This page stopped working
        </h1>
        <p className="mt-2 max-w-md text-body-md text-text-secondary">
          Something went wrong while displaying this view. Your data is safe and nothing was
          lost. Reload to try again.
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <Button onClick={() => window.location.reload()}>Reload page</Button>
          <Button variant="secondary" onClick={() => window.location.assign("/")}>
            Go to dashboard
          </Button>
        </div>
        {import.meta.env.DEV ? (
          <pre className="mt-6 max-w-2xl overflow-x-auto rounded-md border border-border bg-surface-sunken px-3 py-2 text-left font-mono text-caption text-text-subtle">
            {error.message}
          </pre>
        ) : null}
      </div>
    );
  }
}

/** Resets itself on navigation, so the reader can always get out. */
export function ErrorBoundary({ children }: { children: ReactNode }) {
  const location = useLocation();
  return <ErrorBoundaryInner resetKey={location.pathname}>{children}</ErrorBoundaryInner>;
}
