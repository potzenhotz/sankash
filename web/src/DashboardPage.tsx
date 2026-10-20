import { useEffect, useMemo, useState } from "react";

import { Chart, type ChartOption, useChartColors } from "./Chart";
import {
  type FlowKind,
  type FlowSelection,
  groupCategory,
  inPeriod,
  kpis,
  monthPeriod,
  monthsWithData,
  parentMap,
  type Period,
  sankey,
  selectionRows,
  shiftMonth,
  trailingMonths,
  trend,
} from "./dashboard";
import { useCategories, useTransactions } from "./data";

const money = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
const compact = new Intl.NumberFormat("de-DE", { notation: "compact", maximumFractionDigits: 1 });
const monthName = (key: string) =>
  new Date(`${key}-01T00:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
const formatDate = (iso: string) => iso.split("-").reverse().join(".");

const ROLE_LABEL: Record<FlowKind, string> = { income: "Income", account: "Account", expense: "Expenses" };

export function DashboardPage() {
  const transactions = useTransactions();
  const categories = useCategories();
  const colors = useChartColors();

  const all = transactions.data ?? [];
  const months = useMemo(() => monthsWithData(all), [all]);
  const parents = useMemo(() => parentMap(categories.data ?? []), [categories.data]);

  const [period, setPeriod] = useState<Period | null>(null);
  const [account, setAccount] = useState("");
  // 40+ subcategory nodes don't fit a phone screen; start grouped there
  const [byParent, setByParent] = useState(() => window.matchMedia("(max-width: 720px)").matches);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [selection, setSelection] = useState<FlowSelection | null>(null);

  // Default: the most recent month that has data
  useEffect(() => {
    if (!period && months.length) {
      const [y, m] = months[0].split("-").map(Number);
      setPeriod(monthPeriod(y, m));
    }
  }, [period, months]);

  const group = useMemo(
    () => (c: string | null) => groupCategory(c, parents, byParent),
    [parents, byParent],
  );
  const accounts = useMemo(() => [...new Set(all.map((t) => t.account_name ?? ""))].filter(Boolean).sort(), [all]);
  const unfiltered = useMemo(() => (period ? inPeriod(all, period, account, new Set()) : []), [all, period, account]);
  const rows = useMemo(() => (period ? inPeriod(all, period, account, excluded) : []), [all, period, account, excluded]);
  const totals = useMemo(() => kpis(rows), [rows]);
  const flows = useMemo(() => sankey(rows, group), [rows, group]);
  const series = useMemo(() => (period ? trend(rows, period) : null), [rows, period]);
  const periodCategories = useMemo(
    () => [...new Set(unfiltered.map((t) => t.category).filter((c): c is string => !!c))].sort(),
    [unfiltered],
  );
  const detail = useMemo(() => (selection ? selectionRows(rows, selection, group) : []), [rows, selection, group]);

  // The period is a whole calendar month (with or without data) → month navigation applies
  const currentMonth = period && period.start.endsWith("-01") && periodOf(period.start.slice(0, 7)).end === period.end
    ? period.start.slice(0, 7)
    : undefined;
  const monthOptions = currentMonth && !months.includes(currentMonth) ? [currentMonth, ...months].sort().reverse() : months;

  const choose = (next: Period) => {
    setPeriod(next);
    setSelection(null);
  };
  const toggleExcluded = (c: string) =>
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });

  const sankeyOption = useMemo<ChartOption>(() => {
    const label = (id: string) => id.slice(id.indexOf(":") + 1);
    return {
      tooltip: {
        trigger: "item",
        formatter: (p: { dataType: string; data: { source?: string; target?: string; name?: string }; value: number }) =>
          p.dataType === "edge"
            ? `${label(p.data.source!)} → ${label(p.data.target!)}<br/><b>${money.format(p.value)}</b>`
            : `${label(p.data.name!)}<br/><b>${money.format(p.value)}</b>`,
      },
      series: [
        {
          type: "sankey",
          left: 8,
          right: 8,
          top: 8,
          bottom: 8,
          nodeAlign: "justify",
          nodeWidth: 12,
          nodeGap: 14,
          draggable: false,
          emphasis: { focus: "adjacency" },
          labelLayout: { hideOverlap: true },
          label: { color: colors.text, fontSize: 12, formatter: (p: { name: string }) => label(p.name) },
          data: flows.nodes.map((n) => ({
            name: n.id,
            kind: n.kind,
            itemStyle: { color: colors[n.kind], borderColor: colors.surface, borderWidth: 1 },
            // Bold marks accounts in text too, so a category named like an account is not told apart by color alone
            label: { position: n.kind === "expense" ? "left" : "right", fontWeight: n.kind === "account" ? 700 : 400 },
          })),
          links: flows.links.map((l) => ({
            ...l,
            lineStyle: { color: l.source.startsWith("income:") ? colors.income : colors.expense, opacity: 0.28, curveness: 0.5 },
          })),
        },
      ],
    };
  }, [flows, colors]);
  const sankeyHeight = Math.max(380, ...(["income", "account", "expense"] as const).map(
    (k) => flows.nodes.filter((n) => n.kind === k).length * 30,
  ));

  const trendOption = useMemo<ChartOption>(() => {
    if (!series) return {};
    const tick = (d: string) => (series.bucket === "month" ? monthName(d.slice(0, 7)) : formatDate(d).slice(0, 5));
    // Bars: per-bucket totals are discrete amounts, a line would imply values between buckets
    const bar = (name: string, data: number[], color: string) => ({
      name,
      type: "bar",
      data,
      color,
      barMaxWidth: 14,
      barGap: "15%",
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      emphasis: { focus: "series" },
    });
    return {
      grid: { left: 56, right: 12, top: 32, bottom: 28 },
      legend: { top: 0, left: 0, textStyle: { color: colors.muted }, icon: "roundRect", itemWidth: 12, itemHeight: 4 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: colors.grid, opacity: 0.5 } },
        valueFormatter: (v: number) => money.format(v),
      },
      xAxis: {
        type: "category",
        data: series.dates,
        axisLabel: { color: colors.muted, formatter: tick },
        axisLine: { lineStyle: { color: colors.grid } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: colors.grid } },
        axisLabel: { color: colors.muted, formatter: (v: number) => `${compact.format(v)} €` },
      },
      series: [bar("Income", series.income, colors.income), bar("Expenses", series.expense, colors.expense)],
    };
  }, [series, colors]);

  const onSankeyClick = (p: { dataType?: string; data?: unknown }) => {
    const data = p.data as { name?: string; source?: string; target?: string };
    let id = p.dataType === "node" ? data.name : undefined;
    if (p.dataType === "edge") id = data.source?.startsWith("account:") ? data.target : data.source;
    if (!id) return;
    const kind = id.slice(0, id.indexOf(":")) as FlowKind;
    const name = id.slice(id.indexOf(":") + 1);
    setSelection((s) => (s?.kind === kind && s.name === name ? null : { kind, name }));
  };

  const error = transactions.error ?? categories.error;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p className="muted">
          {period ? (currentMonth ? monthName(currentMonth) : `${formatDate(period.start)} – ${formatDate(period.end)}`) : "…"}
          {account ? ` · ${account}` : ""}
        </p>
      </header>

      {error ? <p className="error" role="alert">{error.message}</p> : null}

      <div className="filters">
        <div className="month-nav">
          <button
            type="button"
            className="ghost"
            aria-label="Previous month"
            disabled={!currentMonth}
            onClick={() => currentMonth && choose(periodOf(shiftMonth(currentMonth, -1)))}
          >
            ‹
          </button>
          <select
            aria-label="Month"
            value={currentMonth ?? ""}
            onChange={(e) => e.target.value && choose(periodOf(e.target.value))}
          >
            {!currentMonth ? <option value="">Custom range</option> : null}
            {monthOptions.map((m) => (
              <option key={m} value={m}>{monthName(m)}{months.includes(m) ? "" : " (no data)"}</option>
            ))}
          </select>
          <button
            type="button"
            className="ghost"
            aria-label="Next month"
            disabled={!currentMonth}
            onClick={() => currentMonth && choose(periodOf(shiftMonth(currentMonth, 1)))}
          >
            ›
          </button>
        </div>
        {months.length ? (
          <div className="presets">
            <button type="button" className="ghost" onClick={() => choose(trailingMonths(months[0], 3))}>3 months</button>
            <button type="button" className="ghost" onClick={() => choose(trailingMonths(months[0], 12))}>12 months</button>
            <button type="button" className="ghost" onClick={() => choose({ start: `${months.at(-1)}-01`, end: trailingMonths(months[0], 1).end })}>All</button>
          </div>
        ) : null}
        {period ? (
          <div className="range">
            <input type="date" aria-label="From" value={period.start} max={period.end} onChange={(e) => e.target.value && choose({ ...period, start: e.target.value })} />
            <span className="muted">–</span>
            <input type="date" aria-label="To" value={period.end} min={period.start} onChange={(e) => e.target.value && choose({ ...period, end: e.target.value })} />
          </div>
        ) : null}
        <select aria-label="Account" value={account} onChange={(e) => { setAccount(e.target.value); setSelection(null); }}>
          <option value="">All accounts</option>
          {accounts.map((a) => <option key={a}>{a}</option>)}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={byParent} onChange={(e) => { setByParent(e.target.checked); setSelection(null); }} />
          Group by parent category
        </label>
      </div>

      {periodCategories.length ? (
        <details className="exclude">
          <summary>
            Exclude categories {excluded.size ? <span className="muted">({excluded.size} excluded)</span> : null}
          </summary>
          <div className="chips">
            {periodCategories.map((c) => (
              <button key={c} type="button" aria-pressed={excluded.has(c)} className={excluded.has(c) ? "chip off" : "chip"} onClick={() => toggleExcluded(c)}>
                {c}
              </button>
            ))}
          </div>
          {excluded.size ? <button type="button" className="ghost" onClick={() => setExcluded(new Set())}>Include all</button> : null}
        </details>
      ) : null}

      <section className="kpis" aria-label="Totals">
        <Kpi label="Income" value={money.format(totals.income)} />
        <Kpi label="Expenses" value={money.format(totals.expense)} />
        <Kpi label="Net" value={money.format(totals.net)} tone={totals.net < 0 ? "negative" : "positive"} />
        <a className="kpi kpi-link" href="#/transactions">
          <span className="kpi-label">Uncategorized</span>
          <span className="kpi-value">{totals.uncategorized}</span>
          <span className="kpi-sub">not in the flow chart · categorize →</span>
        </a>
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Money flow</h2>
          <ul className="legend" aria-label="Legend">
            {(["income", "account", "expense"] as const).map((k) => (
              <li key={k}><span className="swatch" style={{ background: colors[k] }} />{ROLE_LABEL[k]}</li>
            ))}
          </ul>
        </div>
        {flows.links.length ? (
          <>
            <Chart option={sankeyOption} height={sankeyHeight} ariaLabel="Money flow from income categories through accounts to expense categories" onClick={onSankeyClick} />
            <p className="hint">Click a category, account or flow to list its transactions.</p>
          </>
        ) : (
          <p className="empty">No categorized transactions in this period.</p>
        )}
        {selection ? (
          <div className="detail">
            <div className="card-head">
              <h3>
                {ROLE_LABEL[selection.kind]}: {selection.name}
                <span className="muted"> · {detail.length} transactions · {money.format(detail.reduce((s, t) => s + t.amount, 0))}</span>
              </h3>
              <button type="button" className="ghost" onClick={() => setSelection(null)} aria-label="Close details">Close</button>
            </div>
            <table className="tx-table compact">
              <thead><tr><th>Date</th><th>Payee</th><th>Category</th><th className="num">Amount</th></tr></thead>
              <tbody>
                {detail.map((t) => (
                  <tr key={t.id}>
                    <td className="date">{formatDate(t.date)}</td>
                    <td className="payee"><div className="payee-name">{t.payee}</div>{t.notes ? <div className="notes">{t.notes}</div> : null}</td>
                    <td className="muted">{t.category}</td>
                    <td className={t.amount < 0 ? "num negative" : "num positive"}>{money.format(t.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Income &amp; expenses over time</h2>
          <span className="muted">per {series?.bucket ?? "day"}</span>
        </div>
        {rows.length ? <Chart option={trendOption} height={320} ariaLabel="Income and expenses over time" /> : <p className="empty">No transactions in this period.</p>}
      </section>

    </div>
  );
}

function periodOf(month: string): Period {
  const [y, m] = month.split("-").map(Number);
  return monthPeriod(y, m);
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <span className={tone ? `kpi-value ${tone}` : "kpi-value"}>{value}</span>
    </div>
  );
}
