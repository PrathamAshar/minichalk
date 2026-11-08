"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api, type Trace } from "@/lib/api";
import { PageHeader, Loading, ErrorState, Empty } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Executions } from "@/components/executions";
import { TraceDetail } from "@/components/trace-detail";
function Traces() {
  const params = useSearchParams();
  const [selected, setSelected] = useState<string | null>(params.get("id"));
  const [filter, setFilter] = useState("all");
  const traces = useQuery({
    queryKey: ["traces", "all"],
    queryFn: () => api<Trace[]>("/traces"),
    refetchInterval: 10000,
  });
  const detail = useQuery({
    queryKey: ["trace", selected],
    queryFn: () => api<Trace>(`/traces/${selected}`),
    enabled: !!selected,
  });
  return (
    <>
      <PageHeader
        eyebrow="EXECUTION OBSERVABILITY"
        title="Trace explorer"
        description="Real query traces, dependency timings, and cache behavior. Nothing simulated."
        action={
          <Button variant="outline" onClick={() => traces.refetch()}>
            <RefreshCw size={14} className={traces.isFetching ? "spin" : ""} />
            Refresh
          </Button>
        }
      />
      <div className="panel">
        <div className="panel-heading">
          <h2>
            Recent queries{" "}
            <span className="subtle-tag">{traces.data?.length ?? 0}</span>
          </h2>
          <select
            aria-label="Filter traces by status"
            className="compact-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="timeout">Timeout</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        {traces.isPending ? (
          <Loading />
        ) : traces.isError ? (
          <ErrorState error={traces.error} retry={() => traces.refetch()} />
        ) : (
          <Executions
            traces={traces.data.filter(
              (t) => filter === "all" || t.status === filter,
            )}
            onSelect={(t) => setSelected(t.query_id)}
            selected={selected || undefined}
          />
        )}
      </div>
      {!selected ? (
        <Empty>
          Select an execution to inspect its timeline and dependency graph.
        </Empty>
      ) : detail.isPending ? (
        <Loading />
      ) : detail.isError ? (
        <ErrorState error={detail.error} />
      ) : (
        <TraceDetail trace={detail.data} />
      )}
    </>
  );
}
export default function TracesPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Traces />
    </Suspense>
  );
}
