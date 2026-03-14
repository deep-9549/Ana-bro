import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.express as px
import plotly.graph_objects as go

dash.register_page(__name__, path="/funnel", name="Funnel")

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
dropdown_options = [{"label": c.title(), "value": c} for c in categories]

# ── Helper: build funnel data ──────────────────────────────────────────────────
EVENT_ORDER  = ["view", "cart", "purchase"]
EVENT_LABELS = {"view": "👁  Views", "cart": "🛒  Added to Cart", "purchase": "💳  Purchases"}
EVENT_COLORS = ["#00e5ff", "#7b61ff", "#00e676"]

def build_funnel(category: str):
    filtered = df.filter(pl.col("category_top") == category) if category else df

    counts = (
        filtered
        .filter(pl.col("event_type").is_in(EVENT_ORDER))
        .group_by("event_type")
        .agg(pl.len().alias("count"))
    )

    # Build ordered dict so funnel always goes view → cart → purchase
    count_map = dict(zip(counts["event_type"].to_list(), counts["count"].to_list()))
    values = [count_map.get(e, 0) for e in EVENT_ORDER]
    labels = [EVENT_LABELS[e] for e in EVENT_ORDER]

    return labels, values


def build_funnel_figure(category: str):
    labels, values = build_funnel(category)

    # Conversion rates
    view_to_cart     = (values[1] / values[0] * 100) if values[0] else 0
    cart_to_purchase = (values[2] / values[1] * 100) if values[1] else 0
    overall          = (values[2] / values[0] * 100) if values[0] else 0

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(
            color=EVENT_COLORS,
            line=dict(width=2, color=["rgba(0,229,255,0.3)", "rgba(123,97,255,0.3)", "rgba(0,230,118,0.3)"])
        ),
        connector=dict(
            line=dict(color="rgba(255,255,255,0.08)", width=1)
        ),
        hovertemplate="<b>%{y}</b><br>Count: %{x:,}<br>Drop-off: %{percentInitial}<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color="#e0e0e0", size=13),
        hoverlabel=dict(
            bgcolor="#1a1a2e",
            bordercolor="#00e5ff",
            font_color="#e0e0e0",
        ),
        annotations=[
            dict(
                x=1.18, y=0.75,
                xref="paper", yref="paper",
                text=f"<b>View → Cart</b><br><span style='color:#7b61ff;font-size:20px'>{view_to_cart:.1f}%</span>",
                showarrow=False,
                align="center",
                font=dict(size=13, color="#888"),
                bgcolor="rgba(20,20,35,0.8)",
                bordercolor="rgba(123,97,255,0.3)",
                borderwidth=1,
                borderpad=10,
            ),
            dict(
                x=1.18, y=0.25,
                xref="paper", yref="paper",
                text=f"<b>Cart → Purchase</b><br><span style='color:#00e676;font-size:20px'>{cart_to_purchase:.1f}%</span>",
                showarrow=False,
                align="center",
                font=dict(size=13, color="#888"),
                bgcolor="rgba(20,20,35,0.8)",
                bordercolor="rgba(0,230,118,0.3)",
                borderwidth=1,
                borderpad=10,
            ),
        ],
    )
    return fig, overall, values


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    # Page Header
    html.Div([
        html.H2("Conversion Funnel"),
        html.P("Analyse drop-off across view → cart → purchase stages"),
    ], className="page-header"),

    # ── Controls Row ───────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Filter by Category", className="section-title"),
            dcc.Dropdown(
                id="category-dropdown",
                options=dropdown_options,
                value=categories[0] if categories else None,
                clearable=False,
                style={
                    "backgroundColor": "#1a1a2e",
                    "color": "#e0e0e0",
                    "border": "1px solid #2a2a3a",
                    "borderRadius": "8px",
                },
            ),
        ], className="glass-card", style={
            "overflow": "visible",
            "position": "relative",
            "zIndex": 9999,
        }), md=4),

        dbc.Col(html.Div([
            html.Div("Overall Conversion", className="kpi-label"),
            html.Div(id="overall-rate", className="kpi-value"),
            html.Div("view → purchase", className="kpi-sub"),
        ], className="kpi-card"), md=2),

        dbc.Col(html.Div([
            html.Div("Total Views", className="kpi-label"),
            html.Div(id="total-views", className="kpi-value text-cyan"),
            html.Div("in this category", className="kpi-sub"),
        ], className="kpi-card"), md=2),

        dbc.Col(html.Div([
            html.Div("Total Purchases", className="kpi-label"),
            html.Div(id="total-purchases", className="kpi-value text-green"),
            html.Div("completed orders", className="kpi-sub"),
        ], className="kpi-card"), md=2),
    ], className="mb-4 g-3", style={"overflow": "visible", "position": "relative", "zIndex": 9999}),

    # ── Funnel Chart ───────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div(id="funnel-title", className="section-title"),
            dcc.Graph(
                id="funnel-graph",
                config={"displayModeBar": False},
                style={"height": "460px"},
            ),
        ], className="glass-card"), width=12),
    ], style={"position": "relative", "zIndex": 1}),

])


# ── Callback ───────────────────────────────────────────────────────────────────
@callback(
    Output("funnel-graph",    "figure"),
    Output("funnel-title",    "children"),
    Output("overall-rate",    "children"),
    Output("total-views",     "children"),
    Output("total-purchases", "children"),
    Input("category-dropdown", "value"),
)
def update_funnel(category):
    fig, overall, values = build_funnel_figure(category)
    title        = f"Funnel · {category.title() if category else 'All Categories'}"
    overall_text = f"{overall:.2f}%"
    views_text   = f"{values[0]:,}"
    purch_text   = f"{values[2]:,}"
    return fig, title, overall_text, views_text, purch_text