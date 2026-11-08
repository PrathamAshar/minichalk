"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Database,
  GitBranch,
  Layers3,
  Play,
  Timer,
} from "lucide-react";
import { api, type Stats, type Trace } from "@/lib/api";
import { ms, percent } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Empty, ErrorState, Loading, PageHeader } from "@/components/common";
import { Executions } from "@/components/executions";
export default function Overview() {
  const stats = useQuery({
    queryKey: ["stats"],
    queryFn: () => api<Stats>("/stats"),
    refetchInterval: 10000,
  });
  const traces = useQuery({
    queryKey: ["traces"],
    queryFn: () => api<Trace[]>("/traces?limit=8"),
    refetchInterval: 10000,
  });
  return (
    <>
      <PageHeader
        eyebrow="SYSTEM OVERVIEW"
        title="Workspace overview"
        description="A live view of your feature engine, from source data to computed decisions."
        action={
          <Button asChild>
            <Link href="/playground">
              <Play size={14} />
              New query
            </Link>
          </Button>
        }
      />
      <div className="overview-banner">
        <div>
          <span className="subtle-tag">
            <span className="dot blue" /> DEMO WORKSPACE
          </span>
          <h2>Real computation. Visible execution.</h2>
          <p>
            Nine executable Python features. A dependency-aware async engine.
            <br />
            Follow a fraud score all the way back to its sources.
          </p>
          <Link className="text-link" href="/features">
            Explore the feature graph <ArrowRight size={14} />
          </Link>
        </div>
        <div className="mini-architecture">
          <span>
            <Database size={15} />
            SQLite sources
          </span>
          <i />
          <span>
            <GitBranch size={15} />
            Feature DAG
          </span>
          <i />
          <span className="accent">
            <Layers3 size={15} />
            fraud_score
          </span>
          <small>
            PLAN <b>→</b> EXECUTE <b>→</b> OBSERVE
          </small>
        </div>
      </div>
      {stats.isError ? (
        <ErrorState error={stats.error} retry={() => stats.refetch()} />
      ) : stats.isPending ? (
        <Loading />
      ) : (
        <div className="metrics">
          {[
            {
              label: "Registered features",
              value: String(stats.data.registered_features),
              note: "Executable Python definitions",
              icon: GitBranch,
            },
            {
              label: "Recent queries",
              value: String(stats.data.query_count),
              note: `${stats.data.successful_queries} successful executions`,
              icon: Layers3,
            },
            {
              label: "Median latency",
              value: ms(stats.data.median_ms),
              note: `P95 ${ms(stats.data.p95_ms)}`,
              icon: Timer,
            },
            {
              label: "Cache hit rate",
              value: percent(stats.data.cache_hit_rate),
              note: `${stats.data.cache_lookups} observed lookups`,
              icon: Database,
            },
          ].map(({ label, value, note, icon: Icon }) => (
            <div className="metric" key={label}>
              <div>
                {label}
                <Icon size={14} />
              </div>
              <strong>{value}</strong>
              <small>{note}</small>
            </div>
          ))}
        </div>
      )}
      <div className="panel">
        <div className="panel-heading">
          <h2>
            Recent executions{" "}
            <span className="live-label">
              <span className="dot green" />
              LIVE
            </span>
          </h2>
          <Link href="/traces" className="text-link">
            View all traces <ArrowUpRight size={14} />
          </Link>
        </div>
        {traces.isPending ? (
          <Loading />
        ) : traces.isError ? (
          <ErrorState error={traces.error} retry={() => traces.refetch()} />
        ) : (
          <Executions traces={traces.data} />
        )}
      </div>
      <div className="overview-bottom">
        <div className="panel getting-started">
          <span className="eyebrow">START HERE</span>
          <h2>Inspect a decision in three steps.</h2>
          <ol>
            <li>
              <span>01</span>
              <div>
                Select an entity
                <small>
                  Compare normal and suspicious transaction histories.
                </small>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                Request a feature
                <small>
                  The planner resolves only its transitive dependencies.
                </small>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                Follow the execution
                <small>
                  Inspect cache behavior, parallel work, and returned values.
                </small>
              </div>
            </li>
          </ol>
          <Button variant="outline" asChild>
            <Link href="/playground">
              Open playground <ArrowRight size={14} />
            </Link>
          </Button>
        </div>
        <div className="panel definition-preview">
          <div className="panel-heading">
            <h2>Defined in Python. Executed as a graph.</h2>
            <span className="mono muted">fraud.py</span>
          </div>
          <pre>
            <span className="code-muted">
              # Real functions, explicit dependencies
            </span>
            {"\n"}
            <span className="code-blue">@feature</span>({"\n"}
            {"  "}name=
            <span className="code-string">&quot;user.fraud_score&quot;</span>,
            {"\n"}
            {"  "}dependencies=[{"\n"}
            {"    "}
            <span className="code-string">
              &quot;user.transaction_velocity&quot;
            </span>
            ,{"\n"}
            {"    "}
            <span className="code-string">&quot;user.device_risk&quot;</span>,
            {"\n"}
            {"    "}
            <span className="code-muted"># + merchant risk, spend, amount</span>
            {"\n"}
            {"  "}],{"\n"}
            {"  "}ttl_seconds=<span className="code-blue">15</span>,{"\n"})
            {"\n"}
            <span className="code-blue">async def</span> fraud_score(ctx, deps)
            -&gt; float:{"\n"}
            {"  "}
            <span className="code-blue">return</span> calculate_risk(deps)
          </pre>
          <div className="panel-foot">
            Illustrative excerpt · inspect the complete definition in
            backend/app/features/fraud.py
          </div>
        </div>
      </div>
      <div className="fine-print">
        Metrics reflect the most recent 1,000 persisted queries. Cold queries
        include labeled artificial I/O delays.{" "}
        {stats.data?.query_count === 0 && (
          <Empty>
            Your workspace is ready. Execute a query to populate observations.
          </Empty>
        )}
      </div>
    </>
  );
}
