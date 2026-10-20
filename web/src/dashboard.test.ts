// Run with: npm test (node's built-in runner, TypeScript via type stripping)
import assert from "node:assert/strict";
import { test } from "node:test";

import type { Transaction } from "./api";
import { bucketFor, groupCategory, inPeriod, kpis, monthPeriod, sankey, selectionRows, trailingMonths, trend } from "./dashboard.ts";

const tx = (id: number, date: string, amount: number, category: string | null, account = "Giro"): Transaction => ({
  id, date, amount, category, account_name: account, payee: `p${id}`, notes: null,
  category_source: category ? "rule" : null, is_transfer: false, parent_id: null, import_filename: null,
});

const rows = [
  tx(1, "2026-03-01", 3000, "Gehalt"),
  tx(2, "2026-03-02", -50, "Einkäufe"),
  tx(3, "2026-03-03", -20, "Einkäufe"),
  tx(4, "2026-03-04", 30, "Nebenkosten"), // refund: same category on the income side
  tx(5, "2026-03-05", -100, "Nebenkosten"),
  tx(6, "2026-03-06", -7, null),
  tx(7, "2026-02-28", -999, "Einkäufe"),
];
const parents = new Map([["Gehalt", "Einkommen"], ["Einkäufe", "Lebensmittel"], ["Nebenkosten", "Wohnen"]]);
const sub = (c: string | null) => groupCategory(c, parents, false);

test("periods", () => {
  assert.deepEqual(monthPeriod(2026, 2), { start: "2026-02-01", end: "2026-02-28" });
  assert.deepEqual(trailingMonths("2026-03", 3), { start: "2026-01-01", end: "2026-03-31" });
  assert.equal(bucketFor(monthPeriod(2026, 3)), "day");
  assert.equal(bucketFor(trailingMonths("2026-03", 12)), "week");
});

test("kpis include uncategorized rows, exclusions drop categories", () => {
  const march = inPeriod(rows, monthPeriod(2026, 3), "", new Set());
  assert.deepEqual(kpis(march), { income: 3030, expense: 177, net: 2853, uncategorized: 1 });
  const noRent = inPeriod(rows, monthPeriod(2026, 3), "", new Set(["Nebenkosten"]));
  assert.equal(kpis(noRent).expense, 77);
});

test("sankey keeps income and expense nodes apart and sums links", () => {
  const { nodes, links } = sankey(inPeriod(rows, monthPeriod(2026, 3), "", new Set()), sub);
  assert.deepEqual(nodes.map((n) => n.id).sort(), [
    "account:Giro", "expense:Einkäufe", "expense:Nebenkosten", "income:Gehalt", "income:Nebenkosten",
  ]);
  assert.deepEqual(links.find((l) => l.target === "expense:Einkäufe"), { source: "account:Giro", target: "expense:Einkäufe", value: 70 });

  const grouped = sankey(rows, (c) => groupCategory(c, parents, true));
  assert.ok(grouped.nodes.some((n) => n.id === "expense:Lebensmittel"));
});

test("selection rows respect side and grouping", () => {
  const march = inPeriod(rows, monthPeriod(2026, 3), "", new Set());
  assert.deepEqual(selectionRows(march, { kind: "expense", name: "Nebenkosten" }, sub).map((t) => t.id), [5]);
  assert.deepEqual(selectionRows(march, { kind: "income", name: "Nebenkosten" }, sub).map((t) => t.id), [4]);
  assert.equal(selectionRows(march, { kind: "account", name: "Giro" }, sub).length, 5); // uncategorized left out
});

test("trend is zero-filled per day", () => {
  const t = trend(inPeriod(rows, monthPeriod(2026, 3), "", new Set()), monthPeriod(2026, 3));
  assert.equal(t.dates.length, 31);
  assert.equal(t.expense[1], 50);
  assert.equal(t.income[9], 0);
});
