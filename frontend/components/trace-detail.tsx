"use client";
import type { Trace } from "@/lib/api";
import { ms, shortName } from "@/lib/utils";
import { Status } from "./common";
import { DependencyGraph } from "./graph";
export function TraceDetail({ trace }: { trace: Trace }) {
  const duration = Math.max(trace.duration_ms, 0.001);
  return (
    <div className="trace-detail">
      <div className="panel">
        <div className="panel-heading">
          <h2>
            Execution detail <code>{trace.query_id.slice(0, 8)}</code>
          </h2>
          <Status status={trace.status} />
        </div>
        <div className="trace-meta">
          <div>
            <label>ENTITY</label>
            <code>{trace.entity_id}</code>
          </div>
          <div>
            <label>TOTAL DURATION</label>
            <code>{ms(trace.duration_ms)}</code>
          </div>
          <div>
            <label>REQUESTED</label>
            <code>{trace.requested.map(shortName).join(", ")}</code>
          </div>
        </div>
        {trace.error && (
          <div className="error-state" role="alert">
            {trace.error}
          </div>
        )}
        <div className="timeline-heading">
          <span>Feature execution timeline</span>
          <span className="muted">
            Compute intervals · dependency and queue waits appear as gaps
          </span>
        </div>
        <div className="timeline">
          <div className="timeline-scale">
            <span>0 ms</span>
            <span>{ms(duration / 2)}</span>
            <span>{ms(duration)}</span>
          </div>
          {trace.spans.map((s) => (
            <div className="timeline-row" key={s.name}>
              <div className="timeline-name" title={s.name}>
                {shortName(s.name)}
                <small>
                  {s.cache} · {s.status}
                </small>
              </div>
              <div className="timeline-track">
                <div
                  className={`timeline-bar ${s.cache === "hit" || s.cache === "coalesced" ? "cache-bar" : ""} ${trace.critical_path.includes(s.name) ? "critical" : ""} ${s.status === "failed" ? "failed-bar" : ""}`}
                  style={{
                    left: `${((s.start_ms ?? 0) / duration) * 100}%`,
                    width: `${Math.max(0.5, (s.duration_ms / duration) * 100)}%`,
                    maxWidth: `${100 - ((s.start_ms ?? 0) / duration) * 100}%`,
                  }}
                  title={`${s.name}: ${s.status} / ${s.cache} / start ${ms(s.start_ms)} / duration ${ms(s.duration_ms)}`}
                />
              </div>
              <span className="mono">{ms(s.duration_ms)}</span>
            </div>
          ))}
        </div>
        <div className="panel-foot">
          Highlighted: longest compute-weighted DAG path (
          {ms(trace.critical_path_ms)}). Excludes scheduling, lock waits, and
          SQLite trace persistence.
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <h2>Executed dependency graph</h2>
          <span className="subtle-tag">{trace.spans.length} features</span>
        </div>
        <DependencyGraph graph={trace.graph} spans={trace.spans} />
      </div>
      <details className="panel json-details">
        <summary>Raw trace JSON</summary>
        <pre>{JSON.stringify(trace, null, 2)}</pre>
      </details>
    </div>
  );
}
