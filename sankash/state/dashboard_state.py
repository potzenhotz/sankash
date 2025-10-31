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

    # KPIs
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    uncategorized_count: int = 0

    # Sankey data
    sankey_nodes: list[dict] = []
    sankey_links: list[dict] = []

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
