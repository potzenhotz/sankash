"""Dashboard page state management."""

from datetime import date, timedelta

import plotly.graph_objects as go
import reflex as rx

from sankash.services import analytics_service, transaction_service
from sankash.state.base import BaseState


class DashboardState(BaseState):
    """State for dashboard page."""

    state_auto_setters = True  # Explicitly enable auto setters

    loading: bool = False
    error: str = ""

    # Date range
    start_date: str = ""
    end_date: str = ""
    selected_year: int = 0
    selected_month: int = 0
    date_range_days: int = 30  # For slider

    # KPIs
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    uncategorized_count: int = 0

    # Sankey data
    sankey_nodes: list[dict] = []
    sankey_links: list[dict] = []

    # Trend data
    trend_dates: list[str] = []
    trend_expenses: list[float] = []
    trend_income: list[float] = []

    # Available months/years with data
    available_months: list[dict] = []

    @rx.var
    def selected_month_name(self) -> str:
        """Get selected month as name string."""
        if self.selected_month > 0:
            months = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
            return months[self.selected_month - 1]
        return ""

    @rx.var
    def available_month_names(self) -> list[str]:
        """Get list of available month names with data."""
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        # Get unique months from available_months
        month_nums = set()
        for item in self.available_months:
            month_nums.add(item["month"])
        # Return month names for available months, sorted
        return [months[m - 1] for m in sorted(month_nums)]

    @rx.var
    def available_years(self) -> list[str]:
        """Get list of available years with data."""
        # Get unique years from available_months
        year_nums = set()
        for item in self.available_months:
            year_nums.add(item["year"])
        # Return years as strings, sorted descending
        return [str(y) for y in sorted(year_nums, reverse=True)]

    @rx.var
    def sankey_figure(self) -> go.Figure:
        """Create Plotly Sankey diagram figure."""
        if not self.sankey_nodes or not self.sankey_links:
            # Return empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No categorized transactions to display",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="#9ca3af"),
            )
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig

        # Extract node labels
        node_labels = [node["label"] for node in self.sankey_nodes]

        # Extract link data
        sources = [link["source"] for link in self.sankey_links]
        targets = [link["target"] for link in self.sankey_links]
        values = [link["value"] for link in self.sankey_links]

        # Create color palette for nodes (mix of blues, greens, purples)
        node_colors = [
            "#7fb4ca",  # Bright blue
            "#98bb6c",  # Bright green
            "#957fb8",  # Purple
            "#e6c384",  # Yellow
            "#7aa89f",  # Cyan
            "#c34043",  # Red
            "#76946a",  # Green
            "#c0a36e",  # Gold
            "#7e9cd8",  # Blue
            "#6a9589",  # Teal
        ]

        # Assign colors to nodes (cycle through palette)
        node_color_list = [node_colors[i % len(node_colors)] for i in range(len(node_labels))]

        # Create semi-transparent link colors based on source node color
        link_colors = [f"rgba({int(node_colors[src % len(node_colors)][1:3], 16)}, {int(node_colors[src % len(node_colors)][3:5], 16)}, {int(node_colors[src % len(node_colors)][5:7], 16)}, 0.4)" for src in sources]

        # Create Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                pad=20,
                thickness=25,
                line=dict(color="white", width=2),
                label=node_labels,
                color=node_color_list,
                hovertemplate='%{label}<br>Total: €%{value:,.2f}<extra></extra>',
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate='%{source.label} → %{target.label}<br>Amount: €%{value:,.2f}<extra></extra>',
            )
        )])

        fig.update_layout(
            title=dict(
                text="💰 Money Flow Analysis",
                font=dict(size=20, family="Arial, sans-serif", color="#1f2937"),
                x=0.5,
                xanchor="center",
            ),
            font=dict(size=13, family="Arial, sans-serif", color="#374151"),
            height=600,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(
                bgcolor="white",
                font_size=13,
                font_family="Arial, sans-serif"
            ),
        )

        return fig

    @rx.var
    def expenses_trend_figure(self) -> go.Figure:
        """Create expenses over time line chart."""
        if not self.trend_dates or not self.trend_expenses:
            # Return empty figure
            fig = go.Figure()
            fig.add_annotation(
                text="No expense data for this period",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="#9ca3af"),
            )
            fig.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return fig

        # Create line chart for expenses over time
        fig = go.Figure()

        # Add expense line
        fig.add_trace(go.Scatter(
            x=self.trend_dates,
            y=self.trend_expenses,
            mode='lines+markers',
            name='Expenses',
            line=dict(color='#c34043', width=3),
            marker=dict(size=6, color='#c34043'),
            fill='tozeroy',
            fillcolor='rgba(195, 64, 67, 0.1)',
            hovertemplate='<b>%{x}</b><br>Expenses: €%{y:,.2f}<extra></extra>',
        ))

        # Add income line for comparison
        if self.trend_income:
            fig.add_trace(go.Scatter(
                x=self.trend_dates,
                y=self.trend_income,
                mode='lines+markers',
                name='Income',
                line=dict(color='#98bb6c', width=3),
                marker=dict(size=6, color='#98bb6c'),
                fill='tozeroy',
                fillcolor='rgba(152, 187, 108, 0.1)',
                hovertemplate='<b>%{x}</b><br>Income: €%{y:,.2f}<extra></extra>',
            ))

        fig.update_layout(
            title=dict(
                text="📊 Income & Expenses Trend",
                font=dict(size=18, family="Arial, sans-serif", color="#1f2937"),
                x=0.5,
                xanchor="center",
            ),
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                zeroline=False,
            ),
            yaxis=dict(
                title="Amount (€)",
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.2)',
            ),
            font=dict(size=12, family="Arial, sans-serif", color="#374151"),
            height=400,
            margin=dict(l=60, r=20, t=60, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.8)",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
        )

        return fig

    def load_dashboard(self) -> None:
        """Load dashboard data."""
        self.loading = True
        self.error = ""

        try:
            # Load available months/years with data
            available_df = analytics_service.get_available_months(self.db_path)
            if not available_df.is_empty():
                self.available_months = available_df.to_dicts()
            else:
                self.available_months = []

            # Set default to current month if not set
            if not self.start_date or not self.end_date:
                from calendar import monthrange
                today = date.today()
                current_year = today.year
                current_month = today.month

                # Check if current month has data, otherwise use most recent month
                has_current_month = any(
                    m["year"] == current_year and m["month"] == current_month
                    for m in self.available_months
                )

                if has_current_month:
                    # Use current month
                    self.selected_year = current_year
                    self.selected_month = current_month
                    start = date(current_year, current_month, 1)
                    _, last_day = monthrange(current_year, current_month)
                    end = date(current_year, current_month, last_day)
                elif self.available_months:
                    # Use most recent month with data
                    most_recent = self.available_months[0]
                    self.selected_year = int(most_recent["year"])
                    self.selected_month = int(most_recent["month"])
                    start = date(self.selected_year, self.selected_month, 1)
                    _, last_day = monthrange(self.selected_year, self.selected_month)
                    end = date(self.selected_year, self.selected_month, last_day)
                else:
                    # No data available, use current month anyway
                    self.selected_year = current_year
                    self.selected_month = current_month
                    start = date(current_year, current_month, 1)
                    _, last_day = monthrange(current_year, current_month)
                    end = date(current_year, current_month, last_day)

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

            # Calculate spending trend (daily aggregation)
            trend_df = analytics_service.calculate_spending_trend(
                self.db_path,
                start,
                end,
                frequency="D",  # Daily
            )

            if not trend_df.is_empty():
                self.trend_dates = [str(d) for d in trend_df["date"].to_list()]
                self.trend_expenses = [float(x) for x in trend_df["expense"].to_list()]
                self.trend_income = [float(x) for x in trend_df["income"].to_list()]
            else:
                self.trend_dates = []
                self.trend_expenses = []
                self.trend_income = []

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

    def set_selected_month(self, month_name: str) -> None:
        """Set selected month from month name."""
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        month_num = months.index(month_name) + 1
        self.selected_month = month_num

        # If year is also set, update the date range
        if self.selected_year > 0:
            self._update_month_year_range()

    def set_selected_year(self, year_str: str) -> None:
        """Set selected year from year string."""
        year_num = int(year_str)
        self.selected_year = year_num

        # If month is also set, update the date range
        if self.selected_month > 0:
            self._update_month_year_range()

    def _update_month_year_range(self) -> None:
        """Update date range based on selected month and year."""
        from calendar import monthrange

        start = date(self.selected_year, self.selected_month, 1)
        _, last_day = monthrange(self.selected_year, self.selected_month)
        end = date(self.selected_year, self.selected_month, last_day)

        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()

    def set_month_year(self, year: int, month: int) -> None:
        """Set period to specific month and year."""
        from calendar import monthrange

        self.selected_year = year
        self.selected_month = month

        # Set start and end dates for the month
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)

        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()

    def set_start_date_input(self, date_str: str) -> None:
        """Set start date from date picker input."""
        self.start_date = date_str
        # Auto-load if end date is also set
        if self.end_date:
            self.load_dashboard()

    def set_end_date_input(self, date_str: str) -> None:
        """Set end date from date picker input."""
        self.end_date = date_str
        # Auto-load if start date is also set
        if self.start_date:
            self.load_dashboard()

    def set_date_range_from_slider(self, values: list[float]) -> None:
        """Set date range based on slider value (days back from today)."""
        days = int(values[0]) if values else 30
        self.date_range_days = days
        end = date.today()
        start = end - timedelta(days=days)
        self.start_date = start.isoformat()
        self.end_date = end.isoformat()
        self.load_dashboard()
