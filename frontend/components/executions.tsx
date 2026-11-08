"use client";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { Trace } from "@/lib/api";
import { ms, percent, shortName } from "@/lib/utils";
import { Status, Empty } from "./common";
export function Executions({
  traces,
  onSelect,
  selected,
}: {
  traces: Trace[];
  onSelect?: (trace: Trace) => void;
  selected?: string;
}) {
  if (!traces.length)
    return (
      <Empty>No executions yet. Run your first query in the playground.</Empty>
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>QUERY / OUTPUT</th>
            <th>ENTITY</th>
            <th>STATUS</th>
            <th>DURATION</th>
            <th>CACHE HITS</th>
            <th>STARTED</th>
            <th>
              <span className="sr-only">Open trace</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr
              key={t.query_id}
              className={selected === t.query_id ? "selected-row" : ""}
            >
              <td>
                {onSelect ? (
                  <button className="table-link" onClick={() => onSelect(t)}>
                    {shortName(t.requested[0])}
                    {t.requested.length > 1
                      ? ` +${t.requested.length - 1}`
                      : ""}
                    <small>{t.query_id.slice(0, 8)}</small>
                  </button>
                ) : (
                  <Link
                    className="table-link"
                    href={`/traces?id=${t.query_id}`}
                  >
                    {shortName(t.requested[0])}
                    <small>{t.query_id.slice(0, 8)}</small>
                  </Link>
                )}
              </td>
              <td className="mono muted">{t.entity_id}</td>
              <td>
                <Status status={t.status} />
              </td>
              <td className="mono">{ms(t.duration_ms)}</td>
              <td className="mono muted">
                {percent(
                  t.spans.filter((s) => ["hit", "coalesced"].includes(s.cache))
                    .length / Math.max(1, t.spans.length),
                )}
              </td>
              <td className="mono muted">
                {new Date(t.started_at).toLocaleTimeString()}
              </td>
              <td>
                {onSelect ? (
                  <button
                    aria-label="Inspect trace"
                    className="icon-button"
                    onClick={() => onSelect(t)}
                  >
                    <ArrowUpRight size={15} />
                  </button>
                ) : (
                  <Link
                    aria-label="Inspect trace"
                    href={`/traces?id=${t.query_id}`}
                  >
                    <ArrowUpRight size={15} />
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
