import { useMemo, useRef, useState } from "react";

import type { Category, RuleField, Transaction } from "./api";
import { CategoryPicker } from "./CategoryPicker";
import { matchesRule, useAddRule } from "./data";

type Props = {
  tx: Transaction;
  all: Transaction[];
  categories: Category[];
  onDone: () => void;
};

/** Inline "when <field> contains <keyword> → category" editor below a row. */
export function RuleEditor({ tx, all, categories, onDone }: Props) {
  const [field, setField] = useState<RuleField>("payee");
  const [value, setValue] = useState(tx.payee);
  const [step, setStep] = useState<"keyword" | "category">("keyword");
  const addRule = useAddRule();
  const keywordRef = useRef<HTMLInputElement>(null);

  const matchCount = useMemo(() => all.filter((t) => matchesRule(t, field, value)).length, [all, field, value]);

  const switchField = (next: RuleField) => {
    setField(next);
    setValue((tx[next] ?? "").trim());
  };

  const create = (category: Category) =>
    addRule.mutate({ category: category.name, field, value: value.trim() }, { onSuccess: onDone });

  return (
    <div
      className="rule-editor"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onDone();
        }
      }}
    >
      <div className="rule-line">
        <span className="muted">When</span>
        <div className="segmented" role="radiogroup" aria-label="Field">
          {(["payee", "notes"] as const).map((f) => (
            <button
              key={f}
              type="button"
              role="radio"
              aria-checked={field === f}
              className={field === f ? "active" : ""}
              onClick={() => switchField(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <span className="muted">contains</span>
        <input
          ref={keywordRef}
          autoFocus
          aria-label="Keyword"
          className="keyword"
          value={value}
          onFocus={(e) => {
            e.target.select();
            setStep("keyword");
          }}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && value.trim()) {
              e.preventDefault();
              setStep("category");
            }
          }}
        />
        <span className={matchCount ? "match-count" : "match-count none"}>
          matches {matchCount} transaction{matchCount === 1 ? "" : "s"}
        </span>
        <button type="button" className="ghost" onClick={onDone} aria-label="Cancel rule">
          Esc
        </button>
      </div>
      {step === "keyword" ? (
        <p className="hint">
          Shorten the keyword to what identifies the merchant, then <kbd>Enter</kbd> to pick the
          category.
        </p>
      ) : (
        <div className="rule-picker">
          <CategoryPicker
            categories={categories.filter((c) => c.parent)}
            placeholder="Rule category… (Enter creates the rule)"
            onSelect={create}
            onCancel={() => {
              setStep("keyword");
              keywordRef.current?.focus();
            }}
          />
        </div>
      )}
      {addRule.error ? <p className="error">Could not create rule: {addRule.error.message}</p> : null}
    </div>
  );
}
