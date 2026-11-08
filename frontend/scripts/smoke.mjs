// Requires an existing Chrome CDP endpoint on :9222 and both MiniChalk services.
// Optional first argument: alternate playwright-core module URL (for WSL/Windows).
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const { chromium } = await import(process.argv[2] || "playwright-core");
const browser = await chromium.connectOverCDP(
  process.env.CDP_URL || "http://127.0.0.1:9222",
);
const screenshots = fileURLToPath(
  new URL("../../docs/screenshots/", import.meta.url),
);
await mkdir(screenshots, { recursive: true });
const base = process.env.BASE_URL || "http://localhost:3000";
const errors = [];
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(e.message));
async function shot(name) {
  await page.screenshot({ path: `${screenshots}/${name}.png`, fullPage: true });
}
async function execute() {
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/query") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Execute query", exact: true })
    .click();
  const trace = await (await response).json();
  assert.equal(trace.status, "success", trace.error);
  await page
    .getByRole("button", { name: "Execute query", exact: true })
    .waitFor();
  return trace;
}
try {
  await page.goto(base);
  await page.locator(".sidebar-bottom").getByText("Engine connected").waitFor();
  await page.getByRole("heading", { name: "Workspace overview" }).waitFor();
  await shot("overview");
  await page
    .locator("nav")
    .getByRole("link", { name: "Query playground" })
    .click();
  await page.locator(".react-flow__node").nth(8).waitFor();
  await page.getByRole("button", { name: "Invalidate entity cache" }).click();
  await page.getByRole("status").filter({ hasText: "Removed" }).waitFor();
  const cold = await execute();
  assert.equal(cold.spans.length, 9);
  assert(cold.spans.every((s) => s.cache === "miss"));
  const device = cold.spans.find((s) => s.name === "user.device_risk");
  const merchant = cold.spans.find((s) => s.name === "user.merchant_risk");
  assert(
    Math.max(device.start_ms, merchant.start_ms) <
      Math.min(device.end_ms, merchant.end_ms),
  );
  await page.locator(".returned-value").waitFor();
  await shot("playground");
  await page
    .getByRole("button", { name: "Execution trace", exact: true })
    .click();
  await page.locator(".timeline-row").nth(8).waitFor();
  await shot("playground-trace");
  const warm = await execute();
  assert(warm.spans.every((s) => s.cache === "hit"));
  await page.getByRole("switch", { name: "Bypass cache" }).click();
  const bypass = await execute();
  assert(bypass.spans.every((s) => s.cache === "bypass"));
  await page
    .locator(".feature-checkboxes")
    .getByText("transaction_count_10m", { exact: true })
    .click();
  const multi = await execute();
  assert.equal(Object.keys(multi.results).length, 2);
  await page.getByLabel("Entity", { exact: true }).selectOption("usr_ada");
  const normal = await execute();
  assert(normal.results["user.fraud_score"] < cold.results["user.fraud_score"]);
  await page
    .locator("nav")
    .getByRole("link", { name: "Feature explorer" })
    .click();
  await page.getByLabel("Search features").fill("transaction_count_10m");
  await page.locator("button.feature-item").click();
  await page
    .getByRole("heading", { name: "user.transaction_count_10m", exact: true })
    .waitFor();
  await page.waitForFunction(
    () => document.querySelectorAll(".react-flow__node").length === 1,
  );
  assert.equal(await page.locator(".react-flow__node").count(), 1);
  await shot("features");
  await page
    .locator("nav")
    .getByRole("link", { name: "Trace explorer" })
    .click();
  await page.locator("tbody .table-link").first().click();
  await page.locator(".timeline-row").nth(8).waitFor();
  await shot("traces");
  await page
    .locator("nav")
    .getByRole("link", { name: "Overview", exact: true })
    .click();
  await page.locator("tbody tr").first().waitFor();
  await shot("overview-populated");
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const mobilePage = await mobile.newPage();
  mobilePage.on("pageerror", (e) => errors.push(e.message));
  await mobilePage.goto(`${base}/playground`);
  await mobilePage.locator(".react-flow__node").nth(8).waitFor();
  assert(
    await mobilePage.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await mobilePage.screenshot({
    path: `${screenshots}/mobile-playground.png`,
    fullPage: true,
  });
  await mobile.close();
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify(
      {
        status: "passed",
        checks: [
          "all four pages",
          "cold query",
          "I/O overlap",
          "warm cache",
          "cache bypass",
          "multiple outputs",
          "entity comparison",
          "feature search",
          "trace timeline",
          "mobile width",
          "no browser exceptions",
        ],
        cold_ms: cold.duration_ms,
        warm_ms: warm.duration_ms,
        suspicious_score: cold.results["user.fraud_score"],
        normal_score: normal.results["user.fraud_score"],
      },
      null,
      2,
    ),
  );
} finally {
  await context.close();
  await browser.close();
}
