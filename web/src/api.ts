// Mirrors the pydantic models in sankash/api/main.py.
// shortcut: hand-written types, switch to openapi-typescript once the API grows past a few endpoints
export type Transaction = {
  id: number;
  date: string;
  payee: string;
  notes: string | null;
  amount: number;
  account_name: string | null;
  category: string | null;
  category_source: "manual" | "rule" | null;
  is_transfer: boolean;
  parent_id: number | null;
  import_filename: string | null;
};

export type Category = {
  name: string;
  parent: string | null;
  display: string;
};

export type RuleField = "payee" | "notes";

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    const message = typeof detail?.detail === "string" ? detail.detail : `${res.status} ${res.statusText}`;
    throw new Error(message);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  transactions: () => request<Transaction[]>("GET", "/api/transactions"),
  categories: () => request<Category[]>("GET", "/api/categories"),
  assignCategory: (id: number, category: string) =>
    request<void>("PUT", `/api/transactions/${id}/category`, { category }),
  resetCategory: (id: number) => request<void>("DELETE", `/api/transactions/${id}/category`),
  addRuleCondition: (category: string, field: RuleField, value: string) =>
    request<void>("POST", "/api/rules/conditions", { category, field, value }),
};
