"""Dashboard page state management."""

from datetime import date, timedelta

import reflex as rx

from sankash.services import analytics_service, transaction_service
from sankash.state.base import BaseState


class DashboardState(BaseState):
    """State for dashboard page."""

    loading: bool = False
    error: str = ""

    # Date range
    start_date: str = ""
    end_date: str = ""

    # KPIs
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    uncategorized_count: int = 0

    # Sankey data
    sankey_nodes: list[dict] = []
    sankey_links: list[dict] = []

    def load_dashboard(self) -> None:
        """Load dashboard data."""
        self.loading = True
        self.error = ""

        try:
            # Set default date range if not set (last 30 days)
            if not self.start_date or not self.end_date:
                end = date.today()
                start = end - timedelta(days=30)
                self.start_date = start.isoformat()
                self.end_date = end.isoformat()

            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)

            # Get transactions for period
            df = analytics_service.get_transactions_for_period(
                self.db_path,
                start,
                end,
            )

            # Calculate KPIs
            kpis = analytics_service.calculate_income_expense(df)
            self.income = kpis["income"]
            self.expense = kpis["expense"]
            self.net = kpis["net"]

            # Get uncategorized count
            self.uncategorized_count = transaction_service.get_uncategorized_count(
                self.db_path
            )

            # Prepare Sankey data
            sankey_data = analytics_service.prepare_sankey_data(df)
            self.sankey_nodes = sankey_data["nodes"]
            self.sankey_links = sankey_data["links"]

        except Exception as e:
            self.error = f"Failed to load dashboard: {str(e)}"
        finally:
            self.loading = False

    def set_period_last_month(self) -> None:
        """Set period to last month."""
        end = date.today()
        start = end - timedelta(days=30)
        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()

    def set_period_last_quarter(self) -> None:
        """Set period to last quarter."""
        end = date.today()
        start = end - timedelta(days=90)
        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()

    def set_period_last_year(self) -> None:
        """Set period to last year."""
        end = date.today()
        start = end - timedelta(days=365)
        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()
