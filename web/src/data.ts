import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type RuleField, type Transaction } from "./api";

const TX_KEY = ["transactions"];

export function useTransactions() {
  return useQuery({ queryKey: TX_KEY, queryFn: api.transactions });
}

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: api.categories, staleTime: Infinity });
}

/** Patch one cached row immediately, roll back on error, refetch afterwards. */
function useOptimisticTxMutation<V>(
  mutationFn: (vars: V) => Promise<void>,
  patch: (tx: Transaction, vars: V) => Transaction | null,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onMutate: async (vars: V) => {
      await qc.cancelQueries({ queryKey: TX_KEY });
      const previous = qc.getQueryData<Transaction[]>(TX_KEY);
      qc.setQueryData<Transaction[]>(TX_KEY, (rows) => rows?.map((tx) => patch(tx, vars) ?? tx));
      return { previous };
    },
    onError: (_err, _vars, ctx) => qc.setQueryData(TX_KEY, ctx?.previous),
    // Rules can change other rows too, so always resync from the server
    onSettled: () => qc.invalidateQueries({ queryKey: TX_KEY }),
  });
}

export function useAssignCategory() {
  return useOptimisticTxMutation(
    ({ id, category }: { id: number; category: string }) => api.assignCategory(id, category),
    (tx, { id, category }) => (tx.id === id ? { ...tx, category, category_source: "manual" } : null),
  );
}

export function useResetCategory() {
  // Server decides which rule applies; just drop the manual marker until the refetch lands
  return useOptimisticTxMutation(
    (id: number) => api.resetCategory(id),
    (tx, id) => (tx.id === id ? { ...tx, category_source: tx.category ? "rule" : null } : null),
  );
}

export function useAddRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ category, field, value }: { category: string; field: RuleField; value: string }) =>
      api.addRuleCondition(category, field, value),
    onSettled: () => qc.invalidateQueries({ queryKey: TX_KEY }),
  });
}

/** Same matching as rule_service._condition_expr for the "contains" operator. */
export function matchesRule(tx: Transaction, field: RuleField, value: string): boolean {
  const needle = value.trim().toLowerCase();
  return needle !== "" && (tx[field] ?? "").toLowerCase().includes(needle);
}
