import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.graph_objects as go
from app import get_df

dash.register_page(__name__, path="/statistics", name="Statistics")

# ── Load Data ──────────────────────────────────────────────────────────────────
df = get_df()

# ── Pre-compute: Top 5 categories by purchase volume ──────────────────────────
top5_categories = (
    df.filter(pl.col("event_type") == "purchase")
    .group_by("category_top")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .head(5)["category_top"]
    .to_list()
)

# ── Pre-compute: Price vs Sales Volume per product ─────────────────────────────
product_stats = (
    df.group_by("product_id").agg([
        pl.col("price").mean().alias("avg_price"),
        pl.col("event_type").filter(pl.col("event_type") == "purchase").len().alias("sales_volume"),
        pl.col("category_top").first().alias("category"),
        pl.col("brand").first().alias("brand"),
    ])
    .filter(
        pl.col("sales_volume") > 0,
        pl.col("avg_price") > 0,
        pl.col("category").is_not_null(),
    )
)

# ── Color map for categories ───────────────────────────────────────────────────
PALETTE = ["#00e5ff", "#7b61ff", "#00e676", "#ff9100", "#ff4081"]

def cat_color(cat):
    idx = top5_categories.index(cat) if cat in top5_categories else 0
    return PALETTE[idx % len(PALETTE)]


# ── Violin Figure ──────────────────────────────────────────────────────────────
def build_violin():
    fig = go.Figure()

    for i, cat in enumerate(top5_categories):
        prices = (
            df.filter(
                (pl.col("category_top") == cat) &
                (pl.col("event_type") == "purchase") &
                (pl.col("price") > 0) &
                (pl.col("price") < pl.col("price").quantile(0.98))
            )["price"]
            .to_list()
        )

        fig.add_trace(go.Violin(
            y=prices,
            name=cat.title(),
            box_visible=True,
            meanline_visible=True,
            fillcolor=f"rgba({','.join(str(int(c*255)) for c in hex_to_rgb(PALETTE[i]))}, 0.15)",
            line_color=PALETTE[i],
            opacity=0.9,
            hoverinfo="y+name",
            points=False,
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        violingap=0.3,
        violinmode="group",
        xaxis=dict(showgrid=False, color="#888", tickfont=dict(size=12)),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#555",
            tickprefix="$",
            tickfont=dict(size=11),
            title="Price (USD)",
            title_font=dict(color="#555", size=11),
        ),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
    )
    return fig


# ── Scatter Figure ─────────────────────────────────────────────────────────────
def build_scatter():
    fig = go.Figure()

    for i, cat in enumerate(top5_categories):
        cat_df = product_stats.filter(pl.col("category") == cat)
        if len(cat_df) == 0:
            continue

        fig.add_trace(go.Scatter(
            x=cat_df["avg_price"].to_list(),
            y=cat_df["sales_volume"].to_list(),
            mode="markers",
            name=cat.title(),
            marker=dict(
                color=PALETTE[i],
                size=7,
                opacity=0.65,
                line=dict(width=0),
            ),
            customdata=list(zip(
                cat_df["brand"].to_list(),
                cat_df["product_id"].to_list(),
            )),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Avg Price: $%{x:,.2f}<br>"
                "Sales: %{y:,}<extra>" + cat.title() + "</extra>"
            ),
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(
            font=dict(color="#888", size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.05)",
            borderwidth=1,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#555",
            tickprefix="$",
            tickfont=dict(size=11),
            title="Average Price (USD)",
            title_font=dict(color="#555", size=11),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#555",
            tickfont=dict(size=11),
            title="Sales Volume (purchases)",
            title_font=dict(color="#555", size=11),
        ),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
    )
    return fig


# ── Utility: hex → rgb tuple (0–1) ────────────────────────────────────────────
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4)]


# ── KPI Stats ──────────────────────────────────────────────────────────────────
purchases_df   = df.filter(pl.col("event_type") == "purchase")
avg_order_val  = purchases_df["price"].mean()
median_price   = purchases_df["price"].median()
price_std      = purchases_df["price"].std()
most_exp_brand = (
    purchases_df
    .group_by("brand")
    .agg(pl.col("price").mean().alias("avg"))
    .sort("avg", descending=True)
    .head(1)["brand"]
    .to_list()
)
most_exp_brand = most_exp_brand[0] if most_exp_brand else "N/A"


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    # Page Header
    html.Div([
        html.H2("Statistical Deep Dive"),
        html.P("Price distributions and product-level sales analysis"),
    ], className="page-header"),

    # ── KPI Row ────────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Avg Order Value", className="kpi-label"),
            html.Div(f"${avg_order_val:,.2f}", className="kpi-value"),
            html.Div("mean purchase price", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),

        dbc.Col(html.Div([
            html.Div("Median Price", className="kpi-label"),
            html.Div(f"${median_price:,.2f}", className="kpi-value text-purple"),
            html.Div("50th percentile", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),

        dbc.Col(html.Div([
            html.Div("Price Std Dev", className="kpi-label"),
            html.Div(f"${price_std:,.2f}", className="kpi-value text-orange"),
            html.Div("price spread", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),

        dbc.Col(html.Div([
            html.Div("Priciest Brand", className="kpi-label"),
            html.Div(most_exp_brand.title(), className="kpi-value text-green",
                     style={"fontSize": "1.4rem"}),
            html.Div("highest avg price", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),
    ], className="mb-4 g-3"),

    # ── Violin Plot ────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div(
                f"Price Distribution · Top 5 Categories  "
                f"({' · '.join(c.title() for c in top5_categories)})",
                className="section-title"
            ),
            dcc.Graph(
                id="violin-graph",
                figure=build_violin(),
                config={"displayModeBar": False},
                style={"height": "360px"},
            ),
        ], className="glass-card"), width=12),
    ], className="mb-4"),

    # ── Scatter Plot ───────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Price vs Sales Volume · Product Level", className="section-title"),
            dcc.Graph(
                id="scatter-graph",
                figure=build_scatter(),
                config={"displayModeBar": False},
                style={"height": "380px"},
            ),
        ], className="glass-card"), width=12),
    ]),

])