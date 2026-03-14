import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.graph_objects as go
import numpy as np

dash.register_page(__name__, path="/geography", name="Geography")

# ── Load Data ──────────────────────────────────────────────────────────────────
df = pl.read_parquet("data/optimized_data.parquet")

# ── Dropdown Options ───────────────────────────────────────────────────────────
categories = (
    df["category_top"]
    .drop_nulls()
    .unique()
    .sort()
    .to_list()
)
dropdown_options = [{"label": "All Categories", "value": "all"}] + [
    {"label": c.title(), "value": c} for c in categories
]

DAYS_ORDER  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOURS       = [f"{h:02d}:00" for h in range(24)]

# ── Helper: build heatmap matrix ───────────────────────────────────────────────
def build_heatmap(event_type: str, category: str):
    filtered = df.filter(pl.col("event_type") == event_type)

    if category != "all":
        filtered = filtered.filter(pl.col("category_top") == category)

    filtered = filtered.with_columns(
        pl.col("event_time").dt.weekday().alias("weekday"),
        pl.col("hour"),
    )

    agg = (
        filtered
        .group_by(["weekday", "hour"])
        .agg(pl.len().alias("count"))
    )

    # Build 7×24 matrix (days × hours)
    matrix = np.zeros((7, 24), dtype=int)
    for row in agg.iter_rows(named=True):
        d = row["weekday"]     # 0=Mon … 6=Sun
        h = row["hour"]
        if 0 <= d < 7 and 0 <= h < 24:
            matrix[d][h] = row["count"]

    return matrix


def build_heatmap_figure(event_type: str, category: str):
    matrix = build_heatmap(event_type, category)

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=HOURS,
        y=DAYS_ORDER,
        colorscale=[
            [0.0,  "rgba(10,10,20,1)"],
            [0.2,  "rgba(0,80,120,1)"],
            [0.5,  "rgba(0,180,220,1)"],
            [0.8,  "rgba(0,229,255,1)"],
            [1.0,  "rgba(180,255,255,1)"],
        ],
        hoverongaps=False,
        hovertemplate="<b>%{y} · %{x}</b><br>Count: %{z:,}<extra></extra>",
        showscale=True,
        colorbar=dict(
            tickfont=dict(color="#888", size=11),
            outlinecolor="rgba(0,0,0,0)",
            bgcolor="rgba(0,0,0,0)",
            thickness=12,
            len=0.8,
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            showgrid=False,
            color="#555",
            tickfont=dict(size=10),
            tickangle=-45,
        ),
        yaxis=dict(
            showgrid=False,
            color="#888",
            tickfont=dict(size=12),
        ),
        hoverlabel=dict(
            bgcolor="#1a1a2e",
            bordercolor="#00e5ff",
            font_color="#e0e0e0",
        ),
    )
    return fig


def build_hourly_bar(category: str):
    filtered = df.filter(pl.col("event_type") == "purchase")
    if category != "all":
        filtered = filtered.filter(pl.col("category_top") == category)

    hourly = (
        filtered
        .group_by("hour")
        .agg(pl.len().alias("count"))
        .sort("hour")
    )

    hours  = hourly["hour"].to_list()
    counts = hourly["count"].to_list()

    # Peak hour gets full cyan, rest fades
    max_c  = max(counts) if counts else 1
    colors = [
        f"rgba(0,229,255,{0.3 + 0.7 * (c / max_c):.2f})" for c in counts
    ]

    fig = go.Figure(go.Bar(
        x=[f"{h:02d}:00" for h in hours],
        y=counts,
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Purchases: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, color="#555", tickfont=dict(size=10), tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#555"),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
    )
    return fig


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    # Page Header
    html.Div([
        html.H2("Temporal Patterns"),
        html.P("When do users browse, add to cart, and purchase?"),
    ], className="page-header"),

    # ── Controls ───────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Filter by Category", className="section-title"),
            dcc.Dropdown(
                id="geo-category-dropdown",
                options=dropdown_options,
                value="all",
                clearable=False,
            ),
        ], className="glass-card", style={"overflow": "visible", "position": "relative", "zIndex": 9999}), md=4),

        dbc.Col(html.Div([
            html.Div("Event Type", className="section-title"),
            dcc.RadioItems(
                id="geo-event-radio",
                options=[
                    {"label": "  👁  Views",    "value": "view"},
                    {"label": "  🛒  Cart",      "value": "cart"},
                    {"label": "  💳  Purchases", "value": "purchase"},
                ],
                value="purchase",
                inline=True,
                inputStyle={"marginRight": "6px", "accentColor": "#00e5ff"},
                labelStyle={"marginRight": "20px", "color": "#888", "fontSize": "0.875rem"},
            ),
        ], className="glass-card"), md=8),

    ], className="mb-4 g-3", style={"overflow": "visible", "position": "relative", "zIndex": 9999}),

    # ── Heatmap ────────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div(id="heatmap-title", className="section-title"),
            dcc.Graph(
                id="heatmap-graph",
                config={"displayModeBar": False},
                style={"height": "320px"},
            ),
        ], className="glass-card"), width=12),
    ], className="mb-4", style={"position": "relative", "zIndex": 1}),

    # ── Hourly Bar ─────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Purchases by Hour of Day", className="section-title"),
            dcc.Graph(
                id="hourly-bar",
                config={"displayModeBar": False},
                style={"height": "260px"},
            ),
        ], className="glass-card"), width=12),
    ], style={"position": "relative", "zIndex": 1}),

])


# ── Callbacks ──────────────────────────────────────────────────────────────────
@callback(
    Output("heatmap-graph", "figure"),
    Output("heatmap-title", "children"),
    Output("hourly-bar",    "figure"),
    Input("geo-event-radio",      "value"),
    Input("geo-category-dropdown","value"),
)
def update_geo(event_type, category):
    label     = event_type.title()
    cat_label = "All Categories" if category == "all" else category.title()
    title     = f"{label} Activity · Day of Week × Hour  ·  {cat_label}"

    heatmap_fig = build_heatmap_figure(event_type, category)
    bar_fig     = build_hourly_bar(category)

    return heatmap_fig, title, bar_fig