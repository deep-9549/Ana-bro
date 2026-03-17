import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.graph_objects as go
import plotly.express as px
from app import get_df

dash.register_page(__name__, path="/advanced", name="Advanced")

df = get_df()

PALETTE = ["#00e5ff","#7b61ff","#00e676","#ff9100","#ff4081",
           "#40c4ff","#b2ff59","#ffd740","#e040fb","#69f0ae"]

# ── Dropdown options ───────────────────────────────────────────────────────────
SCATTER3D_OPTIONS = [
    {"label": "Price × Hour × Sales Volume",     "value": "price_hour_sales"},
    {"label": "Price × Day × Sales Volume",      "value": "price_day_sales"},
    {"label": "Price × Hour × Category",         "value": "price_hour_cat"},
]

RACE_OPTIONS = [
    {"label": "Revenue Race — Top 10 Brands",    "value": "revenue"},
    {"label": "Order Count Race — Top 10 Brands","value": "orders"},
    {"label": "Avg Price Race — Top 10 Brands",  "value": "avg_price"},
]

ANIM_OPTIONS = [
    {"label": "Daily Revenue Over October",      "value": "revenue"},
    {"label": "Daily Orders Over October",       "value": "orders"},
    {"label": "Daily Unique Users Over October", "value": "users"},
]

# ── Pre-compute heavy data once ────────────────────────────────────────────────
_purchases = df.filter(pl.col("event_type") == "purchase")

# Top 10 brands
_top10_brands = (
    _purchases.group_by("brand")
    .agg(pl.len().alias("cnt"))
    .sort("cnt", descending=True)
    .head(10)["brand"].to_list()
)

# Daily metrics
_daily_revenue = (
    _purchases.group_by("date")
    .agg(pl.col("price").sum().alias("revenue"))
    .sort("date")
    .with_columns(pl.col("date").cast(pl.Utf8))
)
_daily_orders = (
    _purchases.group_by("date")
    .agg(pl.len().alias("orders"))
    .sort("date")
    .with_columns(pl.col("date").cast(pl.Utf8))
)
_daily_users = (
    df.group_by("date")
    .agg(pl.col("user_id").n_unique().alias("users"))
    .sort("date")
    .with_columns(pl.col("date").cast(pl.Utf8))
)

# Brand × date data for race
_brand_date = (
    _purchases.filter(pl.col("brand").is_in(_top10_brands))
    .group_by(["date", "brand"])
    .agg([
        pl.col("price").sum().alias("revenue"),
        pl.len().alias("orders"),
        pl.col("price").mean().alias("avg_price"),
    ])
    .sort(["date", "brand"])
    .with_columns(pl.col("date").cast(pl.Utf8))
)


# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    html.Div([
        html.H2("Advanced Visualisations"),
        html.P("3D scatter plots, animated bar race and animated time-series"),
    ], className="page-header"),

    # ── Row 1: 3D Scatter ──────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("3D Scatter Plot", className="section-title"),
            dcc.Dropdown(id="scatter3d-dropdown", options=SCATTER3D_OPTIONS,
                         value="price_hour_sales", clearable=False),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":9999}), md=4),

        dbc.Col(html.Div([
            html.Div(id="scatter3d-title", className="section-title"),
            dcc.Graph(id="scatter3d-graph", config={"displayModeBar": False},
                      style={"height": "420px"}),
        ], className="glass-card"), md=8),
    ], className="mb-4 g-3", style={"overflow":"visible","position":"relative","zIndex":9999}),

    # ── Row 2: Bar Race Animation ──────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Animated Bar Race", className="section-title"),
            dcc.Dropdown(id="race-dropdown", options=RACE_OPTIONS,
                         value="revenue", clearable=False),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":8000}), md=4),

        dbc.Col(html.Div([
            html.Div(id="race-title", className="section-title"),
            dcc.Graph(id="race-graph", config={"displayModeBar": False},
                      style={"height": "420px"}),
        ], className="glass-card"), md=8),
    ], className="mb-4 g-3", style={"overflow":"visible","position":"relative","zIndex":8000}),

    # ── Row 3: Animated Time Series ────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Animated Time Series", className="section-title"),
            dcc.Dropdown(id="anim-dropdown", options=ANIM_OPTIONS,
                         value="revenue", clearable=False),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":7000}), md=4),

        dbc.Col(html.Div([
            html.Div(id="anim-title", className="section-title"),
            dcc.Graph(id="anim-graph", config={"displayModeBar": False},
                      style={"height": "420px"}),
        ], className="glass-card"), md=8),
    ], className="g-3", style={"overflow":"visible","position":"relative","zIndex":7000}),

])


# ── 3D Scatter Callback ────────────────────────────────────────────────────────
@callback(
    Output("scatter3d-graph", "figure"),
    Output("scatter3d-title", "children"),
    Input("scatter3d-dropdown", "value"),
)
def update_scatter3d(metric):
    top5_cats = (
        _purchases.group_by("category_top").agg(pl.len())
        .sort("len", descending=True).head(5)["category_top"].to_list()
    )

    if metric == "price_hour_sales":
        agg = (
            _purchases.filter(pl.col("category_top").is_in(top5_cats))
            .group_by(["product_id", "category_top"])
            .agg([pl.col("price").mean().alias("price"),
                  pl.col("hour").mean().alias("hour"),
                  pl.len().alias("sales")])
            .filter(pl.col("price") < _purchases["price"].quantile(0.97))
        )
        x, y, z = agg["price"].to_list(), agg["hour"].to_list(), agg["sales"].to_list()
        cats = agg["category_top"].to_list()
        xl, yl, zl = "Avg Price ($)", "Avg Purchase Hour", "Sales Volume"
        title = "3D: Price × Hour × Sales Volume"

    elif metric == "price_day_sales":
        agg = (
            _purchases.filter(pl.col("category_top").is_in(top5_cats))
            .with_columns(pl.col("event_time").dt.weekday().alias("wd"))
            .group_by(["product_id", "category_top"])
            .agg([pl.col("price").mean().alias("price"),
                  pl.col("wd").mean().alias("day"),
                  pl.len().alias("sales")])
            .filter(pl.col("price") < _purchases["price"].quantile(0.97))
        )
        x, y, z = agg["price"].to_list(), agg["day"].to_list(), agg["sales"].to_list()
        cats = agg["category_top"].to_list()
        xl, yl, zl = "Avg Price ($)", "Avg Weekday (0=Mon)", "Sales Volume"
        title = "3D: Price × Day of Week × Sales Volume"

    else:  # price_hour_cat
        agg = (
            _purchases.filter(pl.col("category_top").is_in(top5_cats))
            .group_by(["product_id", "category_top"])
            .agg([pl.col("price").mean().alias("price"),
                  pl.col("hour").mean().alias("hour"),
                  pl.len().alias("sales")])
            .filter(pl.col("price") < _purchases["price"].quantile(0.97))
        )
        x, y, z = agg["price"].to_list(), agg["hour"].to_list(), agg["sales"].to_list()
        cats = agg["category_top"].to_list()
        xl, yl, zl = "Avg Price ($)", "Avg Purchase Hour", "Sales Volume"
        title = "3D: Price × Hour × Category"

    cat_idx = {c: i for i, c in enumerate(top5_cats)}
    colors  = [PALETTE[cat_idx.get(c, 0) % len(PALETTE)] for c in cats]

    fig = go.Figure(go.Scatter3d(
        x=x, y=y, z=z,
        mode="markers",
        marker=dict(size=4, color=colors, opacity=0.7, line=dict(width=0)),
        text=cats,
        hovertemplate=f"<b>%{{text}}</b><br>{xl}: %{{x:,.1f}}<br>{yl}: %{{y:,.1f}}<br>{zl}: %{{z:,}}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title=xl, color="#888", gridcolor="rgba(255,255,255,0.08)", backgroundcolor="rgba(0,0,0,0)"),
            yaxis=dict(title=yl, color="#888", gridcolor="rgba(255,255,255,0.08)", backgroundcolor="rgba(0,0,0,0)"),
            zaxis=dict(title=zl, color="#888", gridcolor="rgba(255,255,255,0.08)", backgroundcolor="rgba(0,0,0,0)"),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
    )
    return fig, title


# ── Bar Race Callback ──────────────────────────────────────────────────────────
@callback(
    Output("race-graph", "figure"),
    Output("race-title", "children"),
    Input("race-dropdown", "value"),
)
def update_race(metric):
    metric_map = {
        "revenue":   ("revenue",   "Revenue ($)",      "Revenue Race — Top 10 Brands"),
        "orders":    ("orders",    "Order Count",      "Order Count Race — Top 10 Brands"),
        "avg_price": ("avg_price", "Avg Price ($)",    "Avg Price Race — Top 10 Brands"),
    }
    col, axis_label, title = metric_map[metric]

    dates = sorted(_brand_date["date"].unique().to_list())
    frames = []

    for date in dates:
        day_data = (
            _brand_date.filter(pl.col("date") == date)
            .sort(col, descending=False)
        )
        brands = day_data["brand"].to_list()
        values = day_data[col].to_list()
        bar_colors = [PALETTE[_top10_brands.index(b) % len(PALETTE)] if b in _top10_brands else "#555" for b in brands]

        frames.append(go.Frame(
            data=[go.Bar(
                x=values, y=brands, orientation="h",
                marker=dict(color=bar_colors, line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>" + axis_label + ": %{x:,.0f}<extra></extra>",
            )],
            name=date,
            layout=go.Layout(title_text=f"Date: {date}"),
        ))

    # Initial frame
    first = _brand_date.filter(pl.col("date") == dates[0]).sort(col, descending=False)
    init_brands = first["brand"].to_list()
    init_values = first[col].to_list()
    init_colors = [PALETTE[_top10_brands.index(b) % len(PALETTE)] if b in _top10_brands else "#555" for b in init_brands]

    fig = go.Figure(
        data=[go.Bar(
            x=init_values, y=init_brands, orientation="h",
            marker=dict(color=init_colors, line=dict(width=0)),
        )],
        frames=frames,
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#555", tickfont=dict(size=11)),
            yaxis=dict(showgrid=False, color="#e0e0e0", tickfont=dict(size=12)),
            hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.12, x=0.5, xanchor="center",
                buttons=[
                    dict(label="▶  Play",
                         method="animate",
                         args=[None, {"frame": {"duration": 400, "redraw": True},
                                      "fromcurrent": True, "transition": {"duration": 300}}]),
                    dict(label="⏸  Pause",
                         method="animate",
                         args=[[None], {"frame": {"duration": 0, "redraw": False},
                                        "mode": "immediate", "transition": {"duration": 0}}]),
                ],
                bgcolor="#1a1a2e", bordercolor="#2a2a3a",
                font=dict(color="#e0e0e0"),
            )],
            sliders=[dict(
                steps=[dict(method="animate", args=[[d], {"mode":"immediate",
                            "frame":{"duration":400,"redraw":True},
                            "transition":{"duration":300}}],
                            label=d) for d in dates],
                x=0, y=0, len=1.0,
                bgcolor="#1a1a2e", bordercolor="#2a2a3a",
                font=dict(color="#888", size=10),
                currentvalue=dict(prefix="Date: ", font=dict(color="#00e5ff", size=12)),
                transition=dict(duration=300),
            )],
        ),
    )
    return fig, title


# ── Animated Time Series Callback ──────────────────────────────────────────────
@callback(
    Output("anim-graph", "figure"),
    Output("anim-title", "children"),
    Input("anim-dropdown", "value"),
)
def update_anim(metric):
    if metric == "revenue":
        data   = _daily_revenue
        col    = "revenue"
        color  = "#00e5ff"
        prefix = "$"
        title  = "Daily Revenue — Animated Over October"
    elif metric == "orders":
        data   = _daily_orders
        col    = "orders"
        color  = "#7b61ff"
        prefix = ""
        title  = "Daily Orders — Animated Over October"
    else:
        data   = _daily_users
        col    = "users"
        color  = "#00e676"
        prefix = ""
        title  = "Daily Unique Users — Animated Over October"

    dates  = data["date"].to_list()
    values = data[col].to_list()
    frames = []

    for i in range(1, len(dates) + 1):
        frames.append(go.Frame(
            data=[
                go.Scatter(x=dates[:i], y=values[:i], mode="lines",
                           line=dict(color=color, width=2.5),
                           fill="tozeroy", fillcolor=f"rgba({','.join(str(int(c*255)) for c in _hex_rgb(color))}, 0.06)"),
                go.Scatter(x=[dates[i-1]], y=[values[i-1]], mode="markers",
                           marker=dict(color=color, size=10,
                                       line=dict(color="#0a0a0f", width=2))),
            ],
            name=dates[i-1],
        ))

    fig = go.Figure(
        data=[
            go.Scatter(x=dates[:1], y=values[:1], mode="lines",
                       line=dict(color=color, width=2.5),
                       fill="tozeroy", fillcolor=f"rgba({','.join(str(int(c*255)) for c in _hex_rgb(color))}, 0.06)",
                       hovertemplate=f"<b>%{{x}}</b><br>{prefix}%{{y:,.0f}}<extra></extra>"),
            go.Scatter(x=[dates[0]], y=[values[0]], mode="markers",
                       marker=dict(color=color, size=10, line=dict(color="#0a0a0f", width=2)),
                       hoverinfo="skip"),
        ],
        frames=frames,
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=40, b=10),
            showlegend=False,
            xaxis=dict(showgrid=False, color="#555", tickfont=dict(size=11),
                       range=[dates[0], dates[-1]]),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#555", tickprefix=prefix,
                       range=[0, max(values) * 1.15]),
            hoverlabel=dict(bgcolor="#1a1a2e", bordercolor=color, font_color="#e0e0e0"),
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.12, x=0.5, xanchor="center",
                buttons=[
                    dict(label="▶  Play",
                         method="animate",
                         args=[None, {"frame": {"duration": 120, "redraw": True},
                                      "fromcurrent": True, "transition": {"duration": 80}}]),
                    dict(label="⏸  Pause",
                         method="animate",
                         args=[[None], {"frame": {"duration": 0, "redraw": False},
                                        "mode": "immediate", "transition": {"duration": 0}}]),
                ],
                bgcolor="#1a1a2e", bordercolor="#2a2a3a",
                font=dict(color="#e0e0e0"),
            )],
            sliders=[dict(
                steps=[dict(method="animate",
                            args=[[d], {"mode":"immediate",
                                        "frame":{"duration":120,"redraw":True},
                                        "transition":{"duration":80}}],
                            label=d) for d in dates],
                x=0, y=0, len=1.0,
                bgcolor="#1a1a2e", bordercolor="#2a2a3a",
                font=dict(color="#888", size=10),
                currentvalue=dict(prefix="Date: ", font=dict(color=color, size=12)),
                transition=dict(duration=80),
            )],
        ),
    )
    return fig, title


def _hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]