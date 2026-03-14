import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
from app import get_df

dash.register_page(__name__, path="/", name="Overview")

# ── Load Data ──────────────────────────────────────────────────────────────────
df = get_df()

# ── Pre-compute KPIs ───────────────────────────────────────────────────────────
purchases     = df.filter(pl.col("event_type") == "purchase")
total_revenue = purchases["price"].sum()
total_orders  = len(purchases)
unique_users  = df["user_id"].n_unique()

# ── Pre-compute Time Series ────────────────────────────────────────────────────
daily_revenue = (
    purchases
    .group_by("date")
    .agg(pl.col("price").sum().alias("revenue"))
    .sort("date")
    .with_columns(pl.col("date").cast(pl.Utf8))
)

# ── Pre-compute Top Brands ─────────────────────────────────────────────────────
top_brands = (
    purchases
    .group_by("brand")
    .agg(pl.col("price").sum().alias("revenue"))
    .sort("revenue", descending=True)
    .head(10)
)

# ── Build Charts ───────────────────────────────────────────────────────────────
def make_timeseries():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_revenue["date"].to_list(),
        y=daily_revenue["revenue"].to_list(),
        mode="lines",
        fill="tozeroy",
        line=dict(color="#00e5ff", width=2.5),
        fillcolor="rgba(0, 229, 255, 0.06)",
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            showgrid=False,
            color="#555",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#555",
            tickprefix="$",
            tickfont=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor="#1a1a2e",
            bordercolor="#00e5ff",
            font_color="#e0e0e0",
        ),
    )
    return fig


def make_top_brands():
    brands  = top_brands["brand"].to_list()
    revenue = top_brands["revenue"].to_list()

    # Color gradient: top brand gets full cyan, rest fade to purple
    colors = [
        f"rgba(0, 229, 255, {1.0 - i * 0.08})" for i in range(len(brands))
    ]

    fig = go.Figure(go.Bar(
        x=revenue,
        y=brands,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#555",
            tickprefix="$",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            showgrid=False,
            color="#e0e0e0",
            tickfont=dict(size=12),
            autorange="reversed",
        ),
        hoverlabel=dict(
            bgcolor="#1a1a2e",
            bordercolor="#00e5ff",
            font_color="#e0e0e0",
        ),
    )
    return fig


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    # Page Header
    html.Div([
        html.H2("Overview"),
        html.P("October 2019 · E-Commerce Event Data"),
    ], className="page-header"),

    # ── Row 1: KPI Cards ────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("💰", className="kpi-icon"),
            html.Div("Total Revenue", className="kpi-label"),
            html.Div(f"${total_revenue:,.0f}", className="kpi-value"),
            html.Div("from purchase events", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=4),

        dbc.Col(html.Div([
            html.Div("🛒", className="kpi-icon"),
            html.Div("Total Orders", className="kpi-label"),
            html.Div(f"{total_orders:,}", className="kpi-value text-purple"),
            html.Div("completed purchases", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=4),

        dbc.Col(html.Div([
            html.Div("👤", className="kpi-icon"),
            html.Div("Unique Users", className="kpi-label"),
            html.Div(f"{unique_users:,}", className="kpi-value text-green"),
            html.Div("distinct user IDs", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=4),
    ], className="mb-4 g-3"),

    # ── Row 2: Time Series ──────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Daily Revenue · October 2019", className="section-title"),
            dcc.Graph(
                figure=make_timeseries(),
                config={"displayModeBar": False},
                style={"height": "300px"},
            ),
        ], className="glass-card"), width=12),
    ], className="mb-4"),

    # ── Row 3: Top Brands ───────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Top 10 Brands by Revenue", className="section-title"),
            dcc.Graph(
                figure=make_top_brands(),
                config={"displayModeBar": False},
                style={"height": "360px"},
            ),
        ], className="glass-card"), width=12),
    ]),

])