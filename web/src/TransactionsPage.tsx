import { Fragment, useEffect, useMemo, useRef, useState } from "react";

import type { Category, Transaction } from "./api";
import { CategoryPalette } from "./CategoryPicker";
import { RuleEditor } from "./RuleEditor";
import { useAssignCategory, useCategories, useResetCategory, useTransactions } from "./data";

const money = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

type Sort = { key: "date" | "amount"; desc: boolean };
type Mode = { kind: "pick" | "rule"; id: number } | null;

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

export function TransactionsPage() {
  const transactions = useTransactions();
  const categories = useCategories();
  const assign = useAssignCategory();
  const reset = useResetCategory();

  const [search, setSearch] = useState("");
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const [account, setAccount] = useState("");
  const [sort, setSort] = useState<Sort>({ key: "date", desc: true });
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<Mode>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const all = transactions.data ?? [];
  const cats = categories.data ?? [];
  const displayName = useMemo(() => new Map(cats.map((c) => [c.name, c.display])), [cats]);
  const accounts = useMemo(() => [...new Set(all.map((t) => t.account_name ?? ""))].filter(Boolean).sort(), [all]);
  const uncategorizedCount = useMemo(() => all.filter((t) => !t.category).length, [all]);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = all.filter(
      (t) =>
        (!uncategorizedOnly || !t.category) &&
        (!account || t.account_name === account) &&
        (!q ||
          [t.payee, t.notes, t.category && displayName.get(t.category), money.format(t.amount)].some((v) =>
            (v ?? "").toLowerCase().includes(q),
          )),
    );
    const dir = sort.desc ? -1 : 1;
    return filtered.sort((a, b) =>
      sort.key === "amount" ? (a.amount - b.amount) * dir || b.id - a.id : a.date.localeCompare(b.date) * dir || b.id - a.id,
    );
  }, [all, search, uncategorizedOnly, account, sort, displayName]);

  const current = Math.min(index, Math.max(rows.length - 1, 0));
  const selected: Transaction | undefined = rows[current];
  const modeTx = mode ? all.find((t) => t.id === mode.id) : undefined;

  // Rows disappear when categorized in "uncategorized only"; the index then lands on the next one
  useEffect(() => {
    document.querySelector(`[data-row="${current}"]`)?.scrollIntoView({ block: "nearest" });
  }, [current]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (mode || isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      const actions: Record<string, () => void> = {
        ArrowDown: () => setIndex(Math.min(current + 1, rows.length - 1)),
        j: () => setIndex(Math.min(current + 1, rows.length - 1)),
        ArrowUp: () => setIndex(Math.max(current - 1, 0)),
        k: () => setIndex(Math.max(current - 1, 0)),
        Enter: () => selected && setMode({ kind: "pick", id: selected.id }),
        c: () => selected && setMode({ kind: "pick", id: selected.id }),
        n: () => selected && setMode({ kind: "rule", id: selected.id }),
        r: () => selected?.category_source === "manual" && reset.mutate(selected.id),
        u: () => setUncategorizedOnly((v) => !v),
        "/": () => searchRef.current?.focus(),
      };
      const action = actions[e.key];
      if (action) {
        e.preventDefault();
        action();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, current, rows.length, selected, reset]);

  const pick = (tx: Transaction, category: Category) => {
    setMode(null);
    // Picking what a rule already set is a no-op, not a manual pin
    if (category.name !== tx.category) {
      assign.mutate({ id: tx.id, category: category.name });
    }
  };

  const toggleSort = (key: Sort["key"]) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: true }));

  const error = transactions.error ?? categories.error ?? assign.error ?? reset.error;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Transactions</h1>
          <p className="muted">
            {all.length} transactions · {uncategorizedCount} uncategorized
          </p>
        </div>
      </header>

      <div className="toolbar">
        <input
          ref={searchRef}
          type="search"
          className="search"
          placeholder="Search payee, notes, category, amount"
          aria-label="Search transactions"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setIndex(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape" || e.key === "Enter" || e.key === "ArrowDown") {
              e.preventDefault();
              e.currentTarget.blur();
            }
          }}
        />
        <select aria-label="Account" value={account} onChange={(e) => { setAccount(e.target.value); setIndex(0); }}>
          <option value="">All accounts</option>
          {accounts.map((a) => (
            <option key={a}>{a}</option>
          ))}
        </select>
        <label className="toggle">
          <input type="checkbox" checked={uncategorizedOnly} onChange={(e) => { setUncategorizedOnly(e.target.checked); setIndex(0); }} />
          Uncategorized only
        </label>
        <span className="muted count">{rows.length} shown</span>
      </div>

      {error ? <p className="error" role="alert">{error.message}</p> : null}

      {transactions.isPending ? (
        <p className="muted">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="empty">{uncategorizedOnly ? "Everything is categorized." : "No transactions match."}</p>
      ) : (
        <table className="tx-table">
          <thead>
            <tr>
              <th>
                <button type="button" className="sort" onClick={() => toggleSort("date")}>
                  Date {sort.key === "date" ? (sort.desc ? "↓" : "↑") : ""}
                </button>
              </th>
              <th>Payee</th>
              <th>Account</th>
              <th className="num">
                <button type="button" className="sort" onClick={() => toggleSort("amount")}>
                  Amount {sort.key === "amount" ? (sort.desc ? "↓" : "↑") : ""}
                </button>
              </th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((tx, i) => (
              <Fragment key={tx.id}>
                <tr
                  data-row={i}
                  aria-selected={i === current}
                  className={i === current ? "selected" : undefined}
                  onClick={() => setIndex(i)}
                >
                  <td className="date">{formatDate(tx.date)}</td>
                  <td className="payee">
                    <div className="payee-name">
                      {tx.payee}
                      {tx.parent_id ? <span className="tag">Split</span> : null}
                    </div>
                    {tx.notes ? <div className="notes" title={tx.notes}>{tx.notes}</div> : null}
                  </td>
                  <td className="muted">{tx.account_name}</td>
                  <td className={tx.amount < 0 ? "num negative" : "num positive"}>{money.format(tx.amount)}</td>
                  <td className="category">
                    <button
                      type="button"
                      className={`pill ${tx.category_source ?? "none"}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setIndex(i);
                        setMode({ kind: "pick", id: tx.id });
                      }}
                      title={tx.category_source === "manual" ? "Set manually" : tx.category ? "Set by rule" : undefined}
                    >
                      {tx.category ? displayName.get(tx.category) ?? tx.category : "Uncategorized"}
                    </button>
                    {tx.category_source === "manual" ? (
                      <button
                        type="button"
                        className="icon"
                        aria-label="Reset to rule"
                        title="Let rules decide again (r)"
                        onClick={(e) => {
                          e.stopPropagation();
                          reset.mutate(tx.id);
                        }}
                      >
                        ↺
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="icon"
                      aria-label="Create rule"
                      title="Create rule from this transaction (n)"
                      onClick={(e) => {
                        e.stopPropagation();
                        setIndex(i);
                        setMode({ kind: "rule", id: tx.id });
                      }}
                    >
                      ＋
                    </button>
                  </td>
                </tr>
                {mode?.kind === "rule" && mode.id === tx.id ? (
                  <tr className="editor-row">
                    <td colSpan={5}>
                      <RuleEditor tx={tx} all={all} categories={cats} onDone={() => setMode(null)} />
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      {mode?.kind === "pick" && modeTx ? (
        <CategoryPalette
          categories={cats}
          onSelect={(c) => pick(modeTx, c)}
          onCancel={() => setMode(null)}
          title={
            <>
              <strong>{modeTx.payee}</strong> <span className="muted">{money.format(modeTx.amount)}</span>
            </>
          }
        />
      ) : null}

      <footer className="shortcuts" aria-label="Keyboard shortcuts">
        <span><kbd>↑</kbd><kbd>↓</kbd> / <kbd>j</kbd><kbd>k</kbd> move</span>
        <span><kbd>Enter</kbd> category</span>
        <span><kbd>n</kbd> new rule</span>
        <span><kbd>r</kbd> reset to rule</span>
        <span><kbd>u</kbd> uncategorized</span>
        <span><kbd>/</kbd> search</span>
      </footer>
    </div>
  );
}
