"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Braces,
  Check,
  ChevronRight,
  Loader2,
  Play,
  RotateCcw,
} from "lucide-react";
import {
  api,
  type Entity,
  type Feature,
  type Graph,
  type Trace,
} from "@/lib/api";
import { ms, shortName } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  PageHeader,
  Loading,
  Empty,
  ErrorState,
  Status,
} from "@/components/common";
import { DependencyGraph } from "@/components/graph";
import { TraceDetail } from "@/components/trace-detail";
function Playground() {
  const params = useSearchParams();
  const client = useQueryClient();
  const [entity, setEntity] = useState("usr_nova");
  const [selected, setSelected] = useState<string[]>([
    params.get("feature") || "user.fraud_score",
  ]);
  const [bypass, setBypass] = useState(false);
  const [deadline, setDeadline] = useState("5");
  const [parameters, setParameters] = useState("{}");
  const [view, setView] = useState<"results" | "trace">("results");
  const features = useQuery({
    queryKey: ["features"],
    queryFn: () => api<Feature[]>("/features"),
  });
  const entities = useQuery({
    queryKey: ["entities"],
    queryFn: () => api<Entity[]>("/entities"),
  });
  const graph = useQuery({
    queryKey: ["plan", selected],
    queryFn: () =>
      api<Graph>("/plan", { entity_id: entity, features: selected }),
    enabled: selected.length > 0,
  });
  const execution = useMutation({
    mutationFn: async () => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(parameters);
      } catch {
        throw new Error("Parameters must be valid JSON.");
      }
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
        throw new Error("Parameters must be a JSON object.");
      if (
        !Number.isFinite(Number(deadline)) ||
        Number(deadline) <= 0 ||
        Number(deadline) > 30
      )
        throw new Error("Deadline must be between 0 and 30 seconds.");
      return api<Trace>("/query", {
        entity_id: entity,
        features: selected,
        bypass_cache: bypass,
        parameters: parsed,
        timeout_seconds: Number(deadline),
      });
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["stats"] });
      client.invalidateQueries({ queryKey: ["traces"] });
      setView("results");
    },
  });
  const invalidation = useMutation({
    mutationFn: () =>
      api<{ removed: number }>("/cache/invalidate", { entity_id: entity }),
  });
  const result = execution.data;
  return (
    <>
      <PageHeader
        eyebrow="QUERY PLAYGROUND"
        title="Query playground"
        description="Run a real query against the engine and inspect every step of its execution."
      />
      <div className="playground-layout">
        <section className="panel query-config">
          <div className="panel-heading">
            <h2>
              <Braces size={16} /> Query configuration
            </h2>
          </div>
          <div className="config-body">
            <label className="field-label" htmlFor="entity">
              Entity
            </label>
            {entities.isPending ? (
              <Loading />
            ) : entities.isError ? (
              <ErrorState error={entities.error} />
            ) : (
              <select
                id="entity"
                value={entity}
                onChange={(e) => setEntity(e.target.value)}
              >
                {entities.data.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} · {e.profile}
                  </option>
                ))}
              </select>
            )}
            <span className="field-help mono">{entity}</span>
            <label className="field-label">
              Requested features <span>{selected.length} selected</span>
            </label>
            {features.isPending ? (
              <Loading />
            ) : features.isError ? (
              <ErrorState error={features.error} />
            ) : (
              <div className="feature-checkboxes">
                {features.data.map((f) => (
                  <label
                    key={f.name}
                    className={selected.includes(f.name) ? "checked" : ""}
                  >
                    <input
                      type="checkbox"
                      checked={selected.includes(f.name)}
                      onChange={() =>
                        setSelected((prev) =>
                          prev.includes(f.name)
                            ? prev.filter((n) => n !== f.name)
                            : [...prev, f.name],
                        )
                      }
                    />
                    <span>{shortName(f.name)}</span>
                  </label>
                ))}
              </div>
            )}
            <div className="toggle-field">
              <div>
                <label htmlFor="bypass">Bypass cache</label>
                <small>Compute fresh values for this query</small>
              </div>
              <Switch
                id="bypass"
                checked={bypass}
                onCheckedChange={setBypass}
              />
            </div>
            <details className="advanced">
              <summary>
                Advanced options <ChevronRight size={13} />
              </summary>
              <label className="field-label" htmlFor="deadline">
                Deadline (seconds)
              </label>
              <input
                id="deadline"
                type="number"
                min="0.001"
                max="30"
                step=".1"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
              <label className="field-label" htmlFor="parameters">
                Query parameters (JSON)
              </label>
              <textarea
                id="parameters"
                className="mono"
                value={parameters}
                onChange={(e) => setParameters(e.target.value)}
              />
              <small className="muted">
                Included in cache keys. Demo features use fixed formulas.
              </small>
            </details>
            <Button
              className="run-button"
              disabled={
                execution.isPending ||
                !selected.length ||
                !features.data ||
                !entities.data
              }
              onClick={() => execution.mutate()}
            >
              {execution.isPending ? (
                <Loader2 size={15} className="spin" />
              ) : (
                <Play size={14} />
              )}
              {execution.isPending ? "Executing query…" : "Execute query"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={invalidation.isPending}
              onClick={() => invalidation.mutate()}
            >
              <RotateCcw size={13} />
              Invalidate entity cache
            </Button>
            {invalidation.isSuccess && (
              <span className="field-help" role="status">
                <Check size={12} />
                Removed {invalidation.data.removed} entries
              </span>
            )}
            {invalidation.isError && <ErrorState error={invalidation.error} />}
          </div>
          <div className="config-note">
            <span className="dot blue" />
            Real SQLite data. Artificial 120ms I/O on device and merchant
            sources.
          </div>
        </section>
        <div className="query-output">
          <div className="panel">
            <div className="panel-heading">
              <h2>Dependency plan</h2>
              <span className="subtle-tag">
                {graph.data?.nodes.length ?? 0} features ·{" "}
                {graph.data?.edges.length ?? 0} edges
              </span>
            </div>
            {!selected.length ? (
              <Empty>Select a feature to build a plan.</Empty>
            ) : graph.isPending ? (
              <Loading />
            ) : graph.isError ? (
              <ErrorState error={graph.error} />
            ) : (
              <DependencyGraph graph={graph.data} />
            )}
          </div>
          <div className="panel result-panel">
            <div className="panel-heading">
              <h2>Query response</h2>
              {result && (
                <div className="inline">
                  <Status status={result.status} />
                  <code>{ms(result.duration_ms)}</code>
                </div>
              )}
            </div>
            {execution.isError && <ErrorState error={execution.error} />}
            {execution.isPending ? (
              <Loading />
            ) : !result ? (
              <div className="result-empty">
                <Braces size={28} />
                <h3>Your next decision starts here.</h3>
                <p>
                  Select an entity and features, then execute a query.
                  <br />
                  Computed values and timings will appear here.
                </p>
                <span className="mono">POST /api/query</span>
              </div>
            ) : (
              <>
                <div className="response-tabs">
                  <button
                    className={view === "results" ? "active" : ""}
                    onClick={() => setView("results")}
                  >
                    Returned values
                  </button>
                  <button
                    className={view === "trace" ? "active" : ""}
                    onClick={() => setView("trace")}
                  >
                    Execution trace
                  </button>
                  <Link href={`/traces?id=${result.query_id}`}>
                    Open trace <ArrowUpRight size={13} />
                  </Link>
                </div>
                {result.error && (
                  <div className="error-state" role="alert">
                    {result.error}
                  </div>
                )}
                {view === "results" && (
                  <div className="result-values">
                    {Object.entries(result.results).map(([name, value]) => (
                      <div className="returned-value" key={name}>
                        <span className="mono">{name}</span>
                        <strong>{JSON.stringify(value)}</strong>
                      </div>
                    ))}
                    <details open>
                      <summary>JSON response</summary>
                      <pre>
                        {JSON.stringify(
                          {
                            query_id: result.query_id,
                            status: result.status,
                            results: result.results,
                            duration_ms: result.duration_ms,
                          },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {view === "trace" && result && <TraceDetail trace={result} />}
    </>
  );
}
export default function PlaygroundPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Playground />
    </Suspense>
  );
}
