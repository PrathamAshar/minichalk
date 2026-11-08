import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <AlertCircle size={17} />
      <div>
        {error?.message || "Something went wrong."}
        {retry && (
          <Button variant="outline" size="sm" onClick={retry}>
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}
export function Loading() {
  return (
    <div className="empty" role="status">
      <Loader2 className="spin" size={18} />
      Loading engine data…
    </div>
  );
}
export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Status({ status }: { status: string }) {
  return (
    <span className={`status status-${status}`}>
      <span className="dot" />
      {status}
    </span>
  );
}
