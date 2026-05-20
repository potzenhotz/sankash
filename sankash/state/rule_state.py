"""Rules page state management."""

import json

import reflex as rx

from sankash.core.models import Rule, RuleAction, RuleCondition
from sankash.services import rule_service, category_service, transaction_service
from sankash.services import llm_service, settings_service
from sankash.state.base import BaseState


class RuleState(BaseState):
    """State for rules management — one rule per category, no create/delete."""

    state_auto_setters = True

    # All categories with their rule info (one row per category)
    category_rules: list[dict] = []
    loading: bool = False
    error: str = ""
    success: str = ""
    rule_sort: str = "relevance"  # "relevance" or "alphabetic"

    # Inline editing: which category is currently being edited
    editing_category: str = ""
    conditions: list[dict] = []  # Current conditions being edited

    # Category display mapping
    categories: list[str] = []
    category_display_map: dict[str, str] = {}

    # Uncategorized transactions
    uncategorized_transactions: list[dict] = []
    uncategorized_count: int = 0

    # Per-transaction AI / manual rule creation state
    ai_suggesting_payee: str = ""        # which payee is currently loading/showing
    ai_suggesting_tx_id: int = 0         # which specific transaction row is open (0 = none)
    ai_suggesting_provider: str = ""     # "apfel" or "openrouter"
    ai_loading: bool = False
    ai_error: str = ""
    ai_suggested_category: str = ""      # display name, pre-filled in dropdown
    ai_suggestion_confidence: str = ""
    ai_suggestion_reasoning: str = ""
    ai_match_field: str = "payee"        # "payee" or "notes" — LLM-suggested rule field
    ai_match_value: str = ""             # LLM-suggested keyword for the rule condition

    # Apfel server process
    apfel_running: bool = False

    def load_rules(self) -> None:
        """Load all categories with their rule info."""
        self.loading = True

        try:
            # Run migration on first load
            merges = rule_service.migrate_rules_to_category_based(self.data_dir)
            if merges:
                self.success = f"Migrated rules: merged {merges} duplicate(s)"

            # Get only subcategories (rules don't apply to parent categories)
            cat_df = category_service.get_categories(self.data_dir)
            all_cats = [
                c for c in (cat_df.to_dicts() if not cat_df.is_empty() else [])
                if c.get("parent_category") is not None
            ]

            # Get all rules indexed by target category
            rules_df = rule_service.get_rules(self.data_dir, active_only=False)
            rules_by_category: dict[str, dict] = {}
            if not rules_df.is_empty():
                for rule in rules_df.to_dicts():
                    conditions = json.loads(rule["conditions"]) if isinstance(rule["conditions"], str) else rule["conditions"]
                    actions = json.loads(rule["actions"]) if isinstance(rule["actions"], str) else rule["actions"]
                    target_cat = actions[0]["value"] if actions else ""
                    if target_cat:
                        rules_by_category[target_cat] = {
                            "rule_id": rule["id"],
                            "conditions": conditions,
                            "is_active": rule.get("is_active", True),
                            "priority": rule.get("priority", 0),
                        }

            # Build one row per category
            category_rules = []
            for cat in all_cats:
                cat_name = cat["name"]
                display_name = category_service.get_category_display_name(
                    self.data_dir, cat_name
                )
                rule_info = rules_by_category.get(cat_name, {})
                conditions = rule_info.get("conditions", [])

                # Count matches
                match_count = 0
                if conditions:
                    try:
                        from sankash.core.models import Rule, RuleAction
                        parsed = Rule(
                            name=cat_name,
                            priority=rule_info.get("priority", 0),
                            is_active=rule_info.get("is_active", True),
                            match_type="any",
                            conditions=[RuleCondition(**c) for c in conditions],
                            actions=[RuleAction(action_type="set_category", value=cat_name)],
                        )
                        match_count = rule_service.count_matching_transactions(self.data_dir, parsed)
                    except Exception:
                        pass

                # Format conditions for display
                if conditions:
                    parts = [f"{c['field']} {c['operator']} '{c['value']}'" for c in conditions]
                    condition_text = " OR ".join(parts)
                else:
                    condition_text = ""

                category_rules.append({
                    "category": cat_name,
                    "display_name": display_name,
                    "rule_id": rule_info.get("rule_id", 0),
                    "has_conditions": len(conditions) > 0,
                    "conditions": conditions,
                    "condition_text": condition_text,
                    "condition_count": len(conditions),
                    "match_count": match_count,
                    "is_active": rule_info.get("is_active", True),
                    "priority": rule_info.get("priority", 0),
                })

            self._sort_rules(category_rules)
        except Exception as e:
            self.error = f"Failed to load rules: {str(e)}"
        finally:
            self.loading = False

    def _sort_rules(self, category_rules: list[dict]) -> None:
        """Sort rules by current sort mode and store."""
        if self.rule_sort == "alphabetic":
            category_rules.sort(key=lambda r: r["display_name"].lower())
        else:
            # Relevance: conditions first (by match count desc), then without (alphabetically)
            category_rules.sort(
                key=lambda r: (not r["has_conditions"], -r["match_count"], r["display_name"])
            )
        self.category_rules = category_rules

    def toggle_rule_sort(self) -> None:
        """Toggle between relevance and alphabetic sorting."""
        self.rule_sort = "alphabetic" if self.rule_sort == "relevance" else "relevance"
        self._sort_rules(list(self.category_rules))

    def load_categories(self) -> None:
        """Load category display names for quick-assign."""
        try:
            df = category_service.get_categories(self.data_dir)
            categories = df.to_dicts()

            display_names = []
            display_map = {}

            for cat in categories:
                display_name = category_service.get_category_display_name(
                    self.data_dir, cat["name"]
                )
                display_names.append(display_name)
                display_map[display_name] = cat["name"]

            display_names.sort()
            self.categories = display_names
            self.category_display_map = display_map
        except Exception as e:
            self.error = f"Failed to load categories: {str(e)}"

    def load_uncategorized(self) -> None:
        """Load uncategorized transactions for the side panel."""
        try:
            df, total = transaction_service.get_transactions(
                self.data_dir,
                is_categorized=False,
                sort_by="date",
                sort_order="desc",
                limit=100,
            )
            self.uncategorized_transactions = df.to_dicts() if not df.is_empty() else []
            self.uncategorized_count = total
        except Exception:
            self.uncategorized_transactions = []
            self.uncategorized_count = 0

    # --- Inline editing ---

    def start_editing(self, category: str) -> None:
        """Open inline editor for a category's conditions."""
        self.editing_category = category
        self.error = ""
        self.success = ""

        # Load existing conditions for this category
        existing = rule_service.get_rule_for_category(self.data_dir, category)
        if existing:
            conditions = existing.get("conditions", [])
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
            self.conditions = [dict(c) for c in conditions]
        else:
            self.conditions = []

    def stop_editing(self) -> None:
        """Close inline editor."""
        self.editing_category = ""
        self.conditions = []

    def add_condition(self) -> None:
        """Add empty condition to editor."""
        self.conditions.append({"field": "payee", "operator": "contains", "value": ""})

    def remove_condition(self, index: int) -> None:
        """Remove condition from editor."""
        if 0 <= index < len(self.conditions):
            self.conditions.pop(index)

    def update_condition_field(self, index: int, field: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["field"] = field

    def update_condition_operator(self, index: int, operator: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["operator"] = operator

    def update_condition_value(self, index: int, value: str) -> None:
        if 0 <= index < len(self.conditions):
            self.conditions[index]["value"] = value

    def save_conditions(self):
        """Save conditions for the currently editing category."""
        if not self.editing_category:
            return

        # Validate non-empty values
        for cond in self.conditions:
            if not cond.get("value"):
                self.error = "All conditions must have a value"
                return

        try:
            category = self.editing_category
            existing = rule_service.get_rule_for_category(self.data_dir, category)

            if not self.conditions:
                # No conditions — delete the rule if it exists
                if existing:
                    rule_service.delete_rule(self.data_dir, existing["id"])
                self.editing_category = ""
                self.conditions = []
                self.success = f"Conditions cleared for '{category}'"
                return RuleState.load_rules

            from sankash.core.models import Rule, RuleAction
            rule_conditions = [
                RuleCondition(field=c["field"], operator=c["operator"], value=c["value"])
                for c in self.conditions
            ]

            rule = Rule(
                name=category,
                priority=existing.get("priority", 0) if existing else 0,
                is_active=existing.get("is_active", True) if existing else True,
                match_type="any",
                conditions=rule_conditions,
                actions=[RuleAction(action_type="set_category", value=category)],
            )

            if existing:
                rule_service.update_rule(self.data_dir, existing["id"], rule)
            else:
                rule_service.create_rule(self.data_dir, rule)

            self.editing_category = ""
            self.conditions = []
            self.success = f"Conditions saved for '{category}'"
            return RuleState.load_rules
        except Exception as e:
            self.error = f"Failed to save conditions: {str(e)}"

    def toggle_rule_active(self, category: str, current_active: bool) -> None:
        """Toggle rule active status."""
        try:
            existing = rule_service.get_rule_for_category(self.data_dir, category)
            if not existing:
                return
            rule = rule_service.parse_rule_from_row(existing)
            rule.is_active = not current_active
            rule_service.update_rule(self.data_dir, existing["id"], rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to toggle rule: {str(e)}"

    def update_rule_priority(self, category: str, new_priority: str) -> None:
        """Update rule priority."""
        try:
            existing = rule_service.get_rule_for_category(self.data_dir, category)
            if not existing:
                return
            rule = rule_service.parse_rule_from_row(existing)
            rule.priority = int(new_priority) if new_priority else 0
            rule_service.update_rule(self.data_dir, existing["id"], rule)
            self.load_rules()
        except Exception as e:
            self.error = f"Failed to update priority: {str(e)}"

    # --- Manual rule creation from uncategorized panel ---

    def start_manual_rule(self, payee: str, tx_id: int = 0) -> None:
        """Open inline rule editor for a transaction, pre-filled with its payee."""
        self._clear_ai_state()
        self.ai_suggesting_payee = payee
        self.ai_suggesting_tx_id = tx_id
        self.ai_suggesting_provider = "manual"
        self.ai_match_field = "payee"
        self.ai_match_value = payee
        self.ai_suggested_category = ""

    # --- Apply rules ---

    def apply_rules(self):
        """Apply rules to uncategorized transactions."""
        self.error = ""
        self.success = ""
        try:
            count = rule_service.apply_rules_to_uncategorized(self.data_dir)
            self.success = f"Categorized {count} transactions"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"
        return [RuleState.load_rules, RuleState.load_uncategorized]

    def apply_rules_all(self):
        """Re-apply all rules (rules dominate, manual fallback preserved)."""
        self.error = ""
        self.success = ""
        try:
            count = rule_service.apply_rules_to_all(self.data_dir)
            self.success = f"Re-categorized {count} transactions"
        except Exception as e:
            self.error = f"Failed to apply rules: {str(e)}"
        return [RuleState.load_rules, RuleState.load_uncategorized]

    # --- Apfel server management ---

    def start_apfel(self):
        """Start the Apfel server as a background process."""
        import subprocess
        import time

        try:
            # Check if already reachable
            if llm_service.check_provider_available("apfel", "http://localhost:11434"):
                self.apfel_running = True
                return

            subprocess.Popen(
                ["apfel", "--serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.apfel_running = True
            yield  # show "starting" state

            # Wait briefly for server to come up
            for _ in range(10):
                time.sleep(0.5)
                if llm_service.check_provider_available("apfel", "http://localhost:11434"):
                    return
            self.ai_error = "Apfel started but not yet reachable — try again in a moment"
        except FileNotFoundError:
            self.apfel_running = False
            self.ai_error = (
                "apfel not found. Install with: "
                "brew tap Arthur-Ficial/tap && brew install apfel"
            )
        except Exception as e:
            self.apfel_running = False
            self.ai_error = f"Failed to start Apfel: {e}"

    def check_apfel_status(self) -> None:
        """Check if Apfel server is reachable and update status."""
        self.apfel_running = llm_service.check_provider_available(
            "apfel", "http://localhost:11434"
        )

    # --- Per-transaction AI Suggestion Methods ---

    def _resolve_provider_config(self, provider: str) -> tuple[str, str, str | None]:
        """Return (base_url, model, api_key) for a given provider."""
        if provider == "apfel":
            preset = llm_service.PROVIDER_PRESETS["apfel"]
            return (
                settings_service.get_setting(
                    self.data_dir, "apfel_base_url", preset["default_base_url"]
                ),
                settings_service.get_setting(
                    self.data_dir, "apfel_model", preset["default_model"]
                ),
                None,
            )
        elif provider == "openrouter":
            return (
                settings_service.get_setting(
                    self.data_dir, "openai_base_url", "https://openrouter.ai/api"
                ),
                settings_service.get_setting(
                    self.data_dir, "openai_model",
                    llm_service.PROVIDER_PRESETS["openrouter"]["default_model"],
                ),
                settings_service.get_setting(
                    self.data_dir, "openai_api_key", ""
                ) or None,
            )
        elif provider == "ollama":
            return (
                settings_service.get_setting(
                    self.data_dir, "ollama_base_url", "http://localhost:11434"
                ),
                settings_service.get_setting(
                    self.data_dir, "ollama_model", "llama3.2"
                ),
                None,
            )
        else:
            return (
                settings_service.get_setting(self.data_dir, "openai_base_url", ""),
                settings_service.get_setting(self.data_dir, "openai_model", ""),
                settings_service.get_setting(self.data_dir, "openai_api_key", "") or None,
            )

    def request_ai_suggestion(self, payee: str, provider: str, tx_id: int = 0):
        """Request AI category suggestion for a single transaction."""
        self._clear_ai_state()
        self.ai_suggesting_payee = payee
        self.ai_suggesting_tx_id = tx_id
        self.ai_suggesting_provider = provider
        self.ai_loading = True
        self.ai_error = ""
        self.ai_suggested_category = ""
        self.ai_suggestion_confidence = ""
        self.ai_suggestion_reasoning = ""
        yield  # flush loading state to UI before blocking HTTP call

        try:
            base_url, model, api_key = self._resolve_provider_config(provider)

            if not llm_service.check_provider_available(provider, base_url, api_key):
                label = llm_service.PROVIDER_PRESETS.get(provider, {}).get("label", provider)
                self.ai_error = f"{label} is not reachable at {base_url}. Check Settings."
                self.ai_loading = False
                return

            # Find notes for the specific transaction being suggested.
            # Match by tx_id first (the row the user clicked); fall back to payee
            # match only if no tx_id was provided, otherwise duplicate-payee rows
            # would all be sent the first row's notes.
            notes_sample = ""
            if tx_id:
                for tx in self.uncategorized_transactions:
                    if str(tx.get("id")) == str(tx_id):
                        notes_sample = tx.get("notes", "") or ""
                        break
            else:
                for tx in self.uncategorized_transactions:
                    if tx.get("payee") == payee:
                        notes_sample = tx.get("notes", "") or ""
                        break

            actual_categories = list(self.category_display_map.values())

            suggestions = llm_service.suggest_categories(
                [{"payee": payee, "notes_sample": notes_sample}],
                actual_categories,
                base_url,
                model,
                provider=provider,
                api_key=api_key,
            )

            if suggestions:
                s = suggestions[0]
                actual_cat = s.get("suggested_category", "")
                reverse_map = {v: k for k, v in self.category_display_map.items()}
                self.ai_suggested_category = reverse_map.get(actual_cat, actual_cat)
                self.ai_suggestion_confidence = s.get("confidence", "")
                self.ai_suggestion_reasoning = s.get("reasoning", "")
                self.ai_match_field = s.get("match_field", "payee")
                self.ai_match_value = s.get("match_value", payee)
                # Validate match_field
                if self.ai_match_field not in ("payee", "notes"):
                    self.ai_match_field = "payee"
                # Fallback if LLM didn't return a match_value
                if not self.ai_match_value:
                    self.ai_match_value = payee
            else:
                self.ai_error = "No suggestion returned"
        except Exception as e:
            self.ai_error = f"Suggestion failed: {str(e)}"
        finally:
            self.ai_loading = False

    def update_ai_suggested_category(self, new_cat: str) -> None:
        """User overrides the AI-suggested category in the dropdown."""
        self.ai_suggested_category = new_cat

    def update_ai_match_field(self, field: str) -> None:
        """User overrides the AI-suggested match field."""
        if field not in ("payee", "notes"):
            return
        self.ai_match_field = field
        # Auto-fill value from the transaction so user does not have to retype.
        # Only overwrite when current value still matches the *other* field's
        # value (i.e., user hasn't already customized it).
        tx = next(
            (t for t in self.uncategorized_transactions
             if t.get("id") == self.ai_suggesting_tx_id),
            None,
        )
        if tx is None:
            return
        new_value = (tx.get(field) or "").strip()
        other_value = (tx.get("notes" if field == "payee" else "payee") or "").strip()
        if not self.ai_match_value or self.ai_match_value == other_value:
            self.ai_match_value = new_value

    def update_ai_match_value(self, value: str) -> None:
        """User overrides the AI-suggested match value."""
        self.ai_match_value = value

    def accept_ai_suggestion(self):
        """Accept the current AI suggestion: create a rule and apply it."""
        if not self.ai_match_value or not self.ai_suggested_category:
            return

        try:
            actual_category = self.category_display_map.get(
                self.ai_suggested_category, self.ai_suggested_category
            )
            condition = RuleCondition(
                field=self.ai_match_field,
                operator="contains",
                value=self.ai_match_value,
            )
            rule_service.add_condition_to_category(self.data_dir, actual_category, condition)
            rule_service.apply_rules_to_uncategorized(self.data_dir)
            self.success = f"Rule: {self.ai_match_field} contains '{self.ai_match_value}' → {actual_category}"
            self._clear_ai_state()
        except Exception as e:
            self.ai_error = f"Failed to create rule: {str(e)}"
        return [RuleState.load_rules, RuleState.load_uncategorized]

    def apply_once(self):
        """Categorize matching uncategorized transactions without creating a rule."""
        if not self.ai_suggesting_payee or not self.ai_suggested_category:
            return

        try:
            actual_category = self.category_display_map.get(
                self.ai_suggested_category, self.ai_suggested_category
            )
            # Find all uncategorized transactions matching this payee
            matching_ids = [
                tx["id"] for tx in self.uncategorized_transactions
                if tx.get("payee") == self.ai_suggesting_payee
            ]
            if matching_ids:
                transaction_service.bulk_update_categories(
                    self.data_dir, matching_ids, actual_category, source="manual"
                )
            self.success = f"Categorized {len(matching_ids)} transaction(s) as {actual_category}"
            self._clear_ai_state()
        except Exception as e:
            self.ai_error = f"Failed to categorize: {str(e)}"
        return [RuleState.load_rules, RuleState.load_uncategorized]

    def reject_ai_suggestion(self) -> None:
        """Dismiss the current AI suggestion."""
        self._clear_ai_state()

    def _clear_ai_state(self) -> None:
        """Reset all per-transaction AI state."""
        self.ai_suggesting_payee = ""
        self.ai_suggesting_tx_id = 0
        self.ai_suggesting_provider = ""
        self.ai_loading = False
        self.ai_error = ""
        self.ai_suggested_category = ""
        self.ai_suggestion_confidence = ""
        self.ai_suggestion_reasoning = ""
        self.ai_match_field = "payee"
        self.ai_match_value = ""

    # --- Export/Import ---

    def export_rules(self) -> rx.Component:
        """Export rules as YAML."""
        try:
            yaml_content = rule_service.export_rules(self.data_dir)
            return rx.download(data=yaml_content, filename="rules.yaml")
        except Exception as e:
            self.error = f"Failed to export rules: {str(e)}"

    async def handle_rules_upload(self, files: list[rx.UploadFile]) -> None:
        """Import rules from YAML."""
        if not files:
            return
        try:
            file = files[0]
            content = (await file.read()).decode("utf-8")
            added, updated = rule_service.import_rules(self.data_dir, content)
            self.load_rules()
            self.load_uncategorized()
            self.success = f"Added {added} rules, updated {updated} existing"
        except Exception as e:
            self.error = f"Failed to import rules: {str(e)}"
