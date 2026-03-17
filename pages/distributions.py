import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import polars as pl
import plotly.graph_objects as go
from app import get_df

dash.register_page(__name__, path="/distributions", name="Distributions")

df = get_df()

# ── Dropdown options ───────────────────────────────────────────────────────────
PIE_OPTIONS = [
    {"label": "Category Share of Purchases",  "value": "category"},
    {"label": "Brand Share of Revenue",        "value": "brand_revenue"},
    {"label": "Event Type Split",              "value": "event_type"},
    {"label": "Hour of Day Share of Purchases","value": "hour"},
]

BOX_OPTIONS = [
    {"label": "Price by Top 8 Categories",    "value": "category"},
    {"label": "Price by Top 8 Brands",         "value": "brand"},
    {"label": "Price by Event Type",           "value": "event_type"},
    {"label": "Price by Day of Week",          "value": "weekday"},
]

HIST_OPTIONS = [
    {"label": "Purchase Price Distribution",  "value": "purchase"},
    {"label": "View Price Distribution",      "value": "view"},
    {"label": "Cart Price Distribution",      "value": "cart"},
]

PALETTE = ["#00e5ff","#7b61ff","#00e676","#ff9100","#ff4081",
           "#40c4ff","#b2ff59","#ffd740","#e040fb","#69f0ae"]

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ── Layout ─────────────────────────────────────────────────────────────────────
layout = html.Div([

    html.Div([
        html.H2("Distributions"),
        html.P("Pie charts, box plots and histograms — all dynamically switchable"),
    ], className="page-header"),

    # ── Row 1: Pie Chart ───────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Pie Chart", className="section-title"),
            dcc.Dropdown(
                id="pie-dropdown",
                options=PIE_OPTIONS,
                value="category",
                clearable=False,
            ),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":9999}), md=4),

        dbc.Col(html.Div([
            html.Div(id="pie-title", className="section-title"),
            dcc.Graph(id="pie-graph", config={"displayModeBar": False}, style={"height":"380px"}),
        ], className="glass-card"), md=8),
    ], className="mb-4 g-3", style={"overflow":"visible","position":"relative","zIndex":9999}),

    # ── Row 2: Box Plot ────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Box Plot", className="section-title"),
            dcc.Dropdown(
                id="box-dropdown",
                options=BOX_OPTIONS,
                value="category",
                clearable=False,
            ),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":8000}), md=4),

        dbc.Col(html.Div([
            html.Div(id="box-title", className="section-title"),
            dcc.Graph(id="box-graph", config={"displayModeBar": False}, style={"height":"380px"}),
        ], className="glass-card"), md=8),
    ], className="mb-4 g-3", style={"overflow":"visible","position":"relative","zIndex":8000}),

    # ── Row 3: Histogram ───────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("Histogram", className="section-title"),
            dcc.Dropdown(
                id="hist-dropdown",
                options=HIST_OPTIONS,
                value="purchase",
                clearable=False,
            ),
        ], className="glass-card", style={"overflow":"visible","position":"relative","zIndex":7000}), md=4),

        dbc.Col(html.Div([
            html.Div(id="hist-title", className="section-title"),
            dcc.Graph(id="hist-graph", config={"displayModeBar": False}, style={"height":"380px"}),
        ], className="glass-card"), md=8),
    ], className="g-3", style={"overflow":"visible","position":"relative","zIndex":7000}),

])


# ── Pie Callback ───────────────────────────────────────────────────────────────
@callback(
    Output("pie-graph", "figure"),
    Output("pie-title", "children"),
    Input("pie-dropdown", "value"),
)
def update_pie(metric):
    purchases = df.filter(pl.col("event_type") == "purchase")

    if metric == "category":
        agg = (purchases.group_by("category_top")
               .agg(pl.len().alias("count"))
               .sort("count", descending=True).head(8))
        labels, values = agg["category_top"].to_list(), agg["count"].to_list()
        title = "Category Share of Purchases"

    elif metric == "brand_revenue":
        agg = (purchases.group_by("brand")
               .agg(pl.col("price").sum().alias("revenue"))
               .sort("revenue", descending=True).head(8))
        labels, values = agg["brand"].to_list(), agg["revenue"].to_list()
        title = "Brand Share of Revenue"

    elif metric == "event_type":
        agg = (df.group_by("event_type")
               .agg(pl.len().alias("count")))
        labels, values = agg["event_type"].to_list(), agg["count"].to_list()
        title = "Event Type Split"

    else:  # hour
        agg = (purchases.group_by("hour")
               .agg(pl.len().alias("count"))
               .sort("hour"))
        labels = [f"{h:02d}:00" for h in agg["hour"].to_list()]
        values = agg["count"].to_list()
        title = "Hour of Day Share of Purchases"

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.45,
        marker=dict(colors=PALETTE[:len(labels)],
                    line=dict(color="#0a0a0f", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="#e0e0e0"),
        hovertemplate="<b>%{label}</b><br>Value: %{value:,}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10),
        showlegend=True,
        legend=dict(font=dict(color="#888", size=11), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
        transition={"duration": 500, "easing": "cubic-in-out"},
    )
    return fig, title


# ── Box Callback ───────────────────────────────────────────────────────────────
@callback(
    Output("box-graph", "figure"),
    Output("box-title", "children"),
    Input("box-dropdown", "value"),
)
def update_box(metric):
    purchases = df.filter(pl.col("event_type") == "purchase")
    p98 = purchases["price"].quantile(0.98)
    purchases = purchases.filter(pl.col("price") < p98)

    # Sample max 2000 rows per group — enough for accurate box stats, tiny payload
    SAMPLE = 2000
    records = []

    if metric == "category":
        top = (purchases.group_by("category_top").agg(pl.len())
               .sort("len", descending=True).head(8)["category_top"].to_list())
        for cat in top:
            vals = purchases.filter(pl.col("category_top") == cat)["price"].drop_nulls()
            sample = vals.sample(min(SAMPLE, len(vals)), seed=42).to_list()
            records.append((cat, sample))
        title = "Price Distribution by Top 8 Categories"

    elif metric == "brand":
        top = (purchases.group_by("brand").agg(pl.len())
               .sort("len", descending=True).head(8)["brand"].to_list())
        for b in top:
            vals = purchases.filter(pl.col("brand") == b)["price"].drop_nulls()
            sample = vals.sample(min(SAMPLE, len(vals)), seed=42).to_list()
            records.append((b, sample))
        title = "Price Distribution by Top 8 Brands"

    elif metric == "event_type":
        for e in ["view", "cart", "purchase"]:
            vals = df.filter(pl.col("event_type") == e).filter(
                pl.col("price") > 0, pl.col("price") < p98)["price"].drop_nulls()
            sample = vals.sample(min(SAMPLE, len(vals)), seed=42).to_list()
            records.append((e.title(), sample))
        title = "Price Distribution by Event Type"

    else:  # weekday
        data = purchases.with_columns(pl.col("event_time").dt.weekday().alias("wd"))
        for d in range(7):
            vals = data.filter(pl.col("wd") == d)["price"].drop_nulls()
            if len(vals) < 10:
                continue
            sample = vals.sample(min(SAMPLE, len(vals)), seed=42).to_list()
            records.append((DAYS[d], sample))
        title = "Price Distribution by Day of Week"

    fig = go.Figure()
    for i, (label, sample) in enumerate(records):
        color = PALETTE[i % len(PALETTE)]
        rgba  = f"rgba({','.join(str(int(c*255)) for c in _hex_rgb(color))}, 0.2)"
        fig.add_trace(go.Box(
            y=sample,
            name=label,
            marker_color=color,
            line=dict(color=color, width=1.5),
            fillcolor=rgba,
            boxmean=True,
            boxpoints=False,
            hovertemplate="<b>" + label + "</b><br>$%{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        xaxis=dict(showgrid=False, color="#888", tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#555", tickprefix="$"),
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
        transition={"duration": 400, "easing": "cubic-in-out"},
    )
    return fig, title


# ── Histogram Callback ─────────────────────────────────────────────────────────
@callback(
    Output("hist-graph", "figure"),
    Output("hist-title", "children"),
    Input("hist-dropdown", "value"),
)
def update_hist(event):
    filtered = df.filter(pl.col("event_type") == event)
    p98 = filtered["price"].quantile(0.98)

    # Pre-bin server-side — send ~60 bucket counts, not millions of raw points
    filtered = filtered.filter(pl.col("price") > 0, pl.col("price") < p98)
    min_p = float(filtered["price"].min())
    max_p = float(filtered["price"].max())
    bin_width = (max_p - min_p) / 60

    binned = (
        filtered
        .with_columns(
            ((pl.col("price") - min_p) / bin_width).floor().cast(pl.Int32).alias("bin")
        )
        .group_by("bin")
        .agg(pl.len().alias("count"))
        .sort("bin")
    )

    bin_centers = [min_p + (b + 0.5) * bin_width for b in binned["bin"].to_list()]
    counts = binned["count"].to_list()

    color_map = {"purchase": "#00e5ff", "view": "#7b61ff", "cart": "#00e676"}
    label_map = {"purchase": "Purchase", "view": "View", "cart": "Cart"}
    color = color_map[event]
    title = f"{label_map[event]} Price Distribution"

    fig = go.Figure(go.Bar(
        x=bin_centers,
        y=counts,
        width=[bin_width * 0.9] * len(bin_centers),
        marker=dict(color=color, opacity=0.75, line=dict(width=0)),
        hovertemplate="Price: $%{x:,.0f}<br>Count: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   color="#555", tickprefix="$"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#555"),
        bargap=0.02,
        hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
        transition={"duration": 400, "easing": "cubic-in-out"},
    )
    return fig, title


def _hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]