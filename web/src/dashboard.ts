// Pure dashboard computations over the transactions already loaded for the
// transactions page. Mirrors sankash/services/analytics_service.py.
import type { Category, Transaction } from "./api";

export type Period = { start: string; end: string }; // inclusive ISO dates
export type FlowKind = "income" | "account" | "expense";
export type FlowSelection = { kind: FlowKind; name: string };

export type SankeyNode = { id: string; kind: FlowKind; name: string };
export type SankeyLink = { source: string; target: string; value: number };

const pad = (n: number) => String(n).padStart(2, "0");
const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export function monthPeriod(year: number, month: number): Period {
  return { start: iso(new Date(year, month - 1, 1)), end: iso(new Date(year, month, 0)) };
}

/** "YYYY-MM" keys of months that have transactions, newest first. */
export function monthsWithData(rows: Transaction[]): string[] {
  return [...new Set(rows.map((t) => t.date.slice(0, 7)))].sort().reverse();
}

/** The last `count` full months ending with `lastMonth` ("YYYY-MM"). */
export function trailingMonths(lastMonth: string, count: number): Period {
  const [y, m] = lastMonth.split("-").map(Number);
  return { start: monthPeriod(y, m - count + 1).start, end: monthPeriod(y, m).end };
}

export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

/** Category used for grouping: the subcategory, or its parent when grouped. */
export function groupCategory(
  category: string | null,
  parents: Map<string, string | null>,
  byParent: boolean,
): string | null {
  if (!category) return null;
  return byParent ? parents.get(category) ?? category : category;
}

export function parentMap(categories: Category[]): Map<string, string | null> {
  return new Map(categories.map((c) => [c.name, c.parent]));
}

export function inPeriod(rows: Transaction[], period: Period, account: string, excluded: Set<string>) {
  return rows.filter(
    (t) =>
      t.date >= period.start &&
      t.date <= period.end &&
      (!account || t.account_name === account) &&
      !(t.category && excluded.has(t.category)),
  );
}

export function kpis(rows: Transaction[]) {
  let income = 0;
  let expense = 0;
  let uncategorized = 0;
  for (const t of rows) {
    if (t.amount > 0) income += t.amount;
    else expense -= t.amount;
    if (!t.category) uncategorized += 1;
  }
  return { income, expense, net: income - expense, uncategorized };
}

/** Income categories → accounts → expense categories; uncategorized rows are left out. */
export function sankey(rows: Transaction[], group: (category: string | null) => string | null) {
  const nodes = new Map<string, SankeyNode>();
  const links = new Map<string, SankeyLink>();
  const node = (kind: FlowKind, name: string) => {
    const id = `${kind}:${name}`; // income and expense may share a category name
    if (!nodes.has(id)) nodes.set(id, { id, kind, name });
    return id;
  };
  const add = (source: string, target: string, value: number) => {
    const key = `${source}→${target}`;
    const link = links.get(key) ?? { source, target, value: 0 };
    link.value += value;
    links.set(key, link);
  };

  for (const t of rows) {
    const category = group(t.category);
    if (!category || !t.account_name || t.amount === 0) continue;
    const account = node("account", t.account_name);
    if (t.amount > 0) add(node("income", category), account, t.amount);
    else add(account, node("expense", category), -t.amount);
  }
  return { nodes: [...nodes.values()], links: [...links.values()] };
}

/** Rows behind a clicked node; for an account, all its categorized flows. */
export function selectionRows(
  rows: Transaction[],
  sel: FlowSelection,
  group: (category: string | null) => string | null,
): Transaction[] {
  const picked = rows.filter((t) => {
    if (!group(t.category) || !t.account_name) return false;
    if (sel.kind === "account") return t.account_name === sel.name;
    return group(t.category) === sel.name && (sel.kind === "income" ? t.amount > 0 : t.amount < 0);
  });
  return picked.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);
}

export type Bucket = "day" | "week" | "month";

export function bucketFor(period: Period): Bucket {
  const days = (Date.parse(period.end) - Date.parse(period.start)) / 86_400_000 + 1;
  return days <= 62 ? "day" : days <= 370 ? "week" : "month";
}

function bucketStart(isoDate: string, bucket: Bucket): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  if (bucket === "month") return `${y}-${pad(m)}-01`;
  if (bucket === "day") return isoDate;
  const date = new Date(y, m - 1, d);
  date.setDate(d - ((date.getDay() + 6) % 7)); // back to Monday
  return iso(date);
}

/** Income and expense totals per bucket, zero-filled so gaps read as zero, not as a line jump. */
export function trend(rows: Transaction[], period: Period) {
  const bucket = bucketFor(period);
  const totals = new Map<string, { income: number; expense: number }>();
  const [sy, sm, sd] = period.start.split("-").map(Number);
  for (let d = new Date(sy, sm - 1, sd); iso(d) <= period.end; d.setDate(d.getDate() + 1)) {
    const key = bucketStart(iso(d), bucket);
    if (!totals.has(key)) totals.set(key, { income: 0, expense: 0 });
  }
  for (const t of rows) {
    const entry = totals.get(bucketStart(t.date, bucket));
    if (!entry) continue;
    if (t.amount > 0) entry.income += t.amount;
    else entry.expense -= t.amount;
  }
  const keys = [...totals.keys()].sort();
  return {
    bucket,
    dates: keys,
    income: keys.map((k) => round2(totals.get(k)!.income)),
    expense: keys.map((k) => round2(totals.get(k)!.expense)),
  };
}

const round2 = (n: number) => Math.round(n * 100) / 100;
