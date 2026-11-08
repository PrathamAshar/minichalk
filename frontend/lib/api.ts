import type { components } from "./schema";
export type Feature = components["schemas"]["FeatureMetadata"];
export type Graph = components["schemas"]["Graph"];
export type Trace = components["schemas"]["Trace"];
export type Span = components["schemas"]["Span"];
export type Entity = components["schemas"]["Entity"];
export type Stats = components["schemas"]["Stats"];
export type QueryInput = components["schemas"]["QueryRequest"];
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(
    `/api${path}`,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${res.status}): ${JSON.stringify(data?.detail || res.statusText)}`,
    );
  }
  return res.json();
}
