"use client";
import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  Position,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import type { Graph, Span } from "@/lib/api";
import { ms, shortName } from "@/lib/utils";
export function DependencyGraph({
  graph,
  spans,
  onSelect,
}: {
  graph: Graph;
  spans?: Span[];
  onSelect?: (id: string) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    const layout = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    layout.setGraph({
      rankdir: "LR",
      nodesep: 28,
      ranksep: 64,
      marginx: 20,
      marginy: 20,
    });
    graph.nodes.forEach((n) =>
      layout.setNode(n.id, { width: 228, height: 64 }),
    );
    graph.edges.forEach((e) => layout.setEdge(e.source, e.target));
    dagre.layout(layout);
    return {
      nodes: graph.nodes.map((n) => {
        const span = spans?.find((s) => s.name === n.id);
        const position = layout.node(n.id);
        return {
          id: n.id,
          position: { x: position.x - 114, y: position.y - 32 },
          targetPosition: Position.Left,
          sourcePosition: Position.Right,
          className: n.requested ? "requested-node" : "",
          data: {
            label: (
              <div className="graph-label">
                <span>{shortName(n.id)}</span>
                <small>
                  {span
                    ? `${span.cache} · ${ms(span.duration_ms)}`
                    : n.requested
                      ? "REQUESTED OUTPUT"
                      : "DEPENDENCY"}
                </small>
              </div>
            ),
          },
        };
      }),
      edges: graph.edges.map((e) => ({
        ...e,
        id: `${e.source}:${e.target}`,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#525a66" },
        style: { stroke: "#525a66", strokeWidth: 1.2 },
      })),
    };
  }, [graph, spans]);
  return (
    <div className="graph-container" aria-label="Feature dependency graph">
      <ReactFlow
        key={graph.order.join(",")}
        nodes={nodes}
        edges={edges}
        colorMode="dark"
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.2}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, n) => onSelect?.(n.id)}
      >
        <Background color="#30343b" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
      <div className="graph-legend">
        <span>
          <i />
          Dependency
        </span>
        <span>
          <i className="requested" />
          Requested output
        </span>
      </div>
    </div>
  );
}
