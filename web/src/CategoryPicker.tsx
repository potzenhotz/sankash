import { Command } from "cmdk";

import type { Category } from "./api";

type Props = {
  categories: Category[];
  onSelect: (category: Category) => void;
  onCancel: () => void;
  placeholder?: string;
};

/** Type-to-filter category list; arrows + Enter to pick, Escape to cancel. */
export function CategoryPicker({ categories, onSelect, onCancel, placeholder = "Category…" }: Props) {
  return (
    <Command
      className="picker"
      label="Choose category"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          onCancel();
        }
      }}
    >
      <Command.Input autoFocus placeholder={placeholder} className="picker-input" />
      <Command.List className="picker-list">
        <Command.Empty className="picker-empty">No category found</Command.Empty>
        {categories.map((c) => (
          <Command.Item
            key={c.name}
            value={c.display}
            onSelect={() => onSelect(c)}
            className="picker-item"
          >
            {c.parent ? <span className="muted">{c.parent} › </span> : null}
            {c.name}
          </Command.Item>
        ))}
      </Command.List>
    </Command>
  );
}

/** Centered command-palette overlay around the picker. */
export function CategoryPalette({
  title,
  ...props
}: Props & { title: React.ReactNode }) {
  return (
    <div className="overlay" onMouseDown={props.onCancel}>
      <div className="palette" role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}>
        <div className="palette-title">{title}</div>
        <CategoryPicker {...props} />
      </div>
    </div>
  );
}
