"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, GitBranch, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { api, type Feature, type Graph, type Trace } from "@/lib/api";
import { shortName } from "@/lib/utils";
import { PageHeader, Loading, ErrorState, Empty } from "@/components/common";
import { DependencyGraph } from "@/components/graph";
import { Executions } from "@/components/executions";
export default function FeaturesPage() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("user.fraud_score");
  const features = useQuery({
    queryKey: ["features"],
    queryFn: () => api<Feature[]>("/features"),
  });
  const graph = useQuery({
    queryKey: ["graph", selected],
    queryFn: () => api<Graph>(`/features/${selected}/graph`),
  });
  const traces = useQuery({
    queryKey: ["feature-traces"],
    queryFn: () => api<Trace[]>("/traces"),
  });
  const feature = features.data?.find((f) => f.name === selected);
  return (
    <>
      <PageHeader
        eyebrow="FEATURE REGISTRY"
        title="Feature explorer"
        description="Discover executable features, inspect their definitions, and follow their dependencies."
      />
      {features.isError ? (
        <ErrorState error={features.error} retry={() => features.refetch()} />
      ) : features.isPending ? (
        <Loading />
      ) : (
        <div className="feature-layout">
          <section className="panel feature-list">
            <div className="search">
              <Search size={15} />
              <input
                aria-label="Search features"
                placeholder="Search features…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <kbd>{features.data.length}</kbd>
            </div>
            <div className="list-label">USER FEATURES</div>
            {features.data
              .filter((f) =>
                f.name.toLowerCase().includes(search.toLowerCase()),
              )
              .map((f) => (
                <button
                  key={f.name}
                  className={`feature-item ${f.name === selected ? "selected" : ""}`}
                  onClick={() => setSelected(f.name)}
                >
                  <GitBranch size={15} />
                  <div>
                    {shortName(f.name)}
                    <small>
                      {f.dependencies.length
                        ? `${f.dependencies.length} dependencies`
                        : "Source feature"}{" "}
                      <span>·</span> TTL {f.ttl_seconds}s
                    </small>
                  </div>
                </button>
              ))}
            {!features.data.some((f) => f.name.includes(search)) && (
              <Empty>No matching features.</Empty>
            )}
          </section>
          <div className="feature-detail">
            {feature && (
              <div className="panel">
                <div className="feature-intro">
                  <span className="eyebrow">FEATURE DEFINITION</span>
                  <h2 className="mono">{feature.name}</h2>
                  <p>{feature.description}</p>
                  <div className="feature-properties">
                    <div>
                      <label>OUTPUT TYPE</label>
                      <code>{String(feature.output_type.type || "JSON")}</code>
                    </div>
                    <div>
                      <label>CACHE TTL</label>
                      <code>{feature.ttl_seconds}s</code>
                    </div>
                    <div>
                      <label>VERSION</label>
                      <code>v{feature.version}</code>
                    </div>
                    <div>
                      <label>DEPENDENCIES</label>
                      <code>{feature.dependencies.length}</code>
                    </div>
                  </div>
                  <Link
                    className="text-link"
                    href={`/playground?feature=${feature.name}`}
                  >
                    Query this feature <ArrowUpRight size={14} />
                  </Link>
                </div>
                <div className="panel-heading">
                  <h2>Dependency graph</h2>
                  <span className="muted">Click a node to inspect</span>
                </div>
                {graph.isPending ? (
                  <Loading />
                ) : graph.isError ? (
                  <ErrorState error={graph.error} />
                ) : (
                  <DependencyGraph graph={graph.data} onSelect={setSelected} />
                )}
              </div>
            )}
            <div className="panel">
              <div className="panel-heading">
                <h2>Recent feature executions</h2>
              </div>
              {traces.isPending ? (
                <Loading />
              ) : traces.isError ? (
                <ErrorState error={traces.error} />
              ) : (
                <Executions
                  traces={traces.data
                    .filter((t) => t.spans.some((s) => s.name === selected))
                    .slice(0, 5)}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
