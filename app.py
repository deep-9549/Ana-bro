import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.io as pio
import plotly.graph_objects as go
import polars as pl

# ── Global Plotly Theme ────────────────────────────────────────────────────────
pio.templates.default = "plotly_dark"

# ── Load Data ONCE globally ────────────────────────────────────────────────────
print("📦 Loading parquet into memory (one time only)...")
_df = pl.read_parquet("data/optimized_data.parquet")
print(f"✅ Data loaded — {_df.shape[0]:,} rows ready.")

def get_df():
    return _df

# ── Pre-build Statistics figures at startup ────────────────────────────────────
print("📊 Pre-building Statistics figures...")

PALETTE = ["#00e5ff", "#7b61ff", "#00e676", "#ff9100", "#ff4081"]

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]

_top5 = (
    _df.filter(pl.col("event_type") == "purchase")
    .group_by("category_top")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .head(5)["category_top"]
    .to_list()
)

_product_stats = (
    _df.group_by("product_id").agg([
        pl.col("price").mean().alias("avg_price"),
        pl.col("event_type").filter(pl.col("event_type") == "purchase").len().alias("sales_volume"),
        pl.col("category_top").first().alias("category"),
        pl.col("brand").first().alias("brand"),
    ])
    .filter(pl.col("sales_volume") > 0, pl.col("avg_price") > 0, pl.col("category").is_not_null())
)

_purchases     = _df.filter(pl.col("event_type") == "purchase")
_avg_order_val = _purchases["price"].mean()
_median_price  = _purchases["price"].median()
_price_std     = _purchases["price"].std()
_top_brand     = (
    _purchases.group_by("brand")
    .agg(pl.col("price").mean().alias("avg"))
    .sort("avg", descending=True)
    .head(1)["brand"].to_list()
)
_top_brand = _top_brand[0] if _top_brand else "N/A"

_violin = go.Figure()
_p98 = _purchases["price"].quantile(0.98)
for i, cat in enumerate(_top5):
    prices = _df.filter(
        (pl.col("category_top") == cat) & (pl.col("event_type") == "purchase") &
        (pl.col("price") > 0) & (pl.col("price") < _p98)
    )["price"].to_list()
    _violin.add_trace(go.Violin(
        y=prices, name=cat.title(), box_visible=True, meanline_visible=True,
        fillcolor=f"rgba({','.join(str(int(c*255)) for c in _hex_to_rgb(PALETTE[i]))}, 0.15)",
        line_color=PALETTE[i], opacity=0.9, hoverinfo="y+name", points=False,
    ))
_violin.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=10, b=10), showlegend=False, violingap=0.3,
    xaxis=dict(showgrid=False, color="#888"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#555",
               tickprefix="$", title="Price (USD)", title_font=dict(color="#555", size=11)),
    hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
)
VIOLIN_JSON = _violin.to_json()

_scatter = go.Figure()
for i, cat in enumerate(_top5):
    cat_df = _product_stats.filter(pl.col("category") == cat)
    if len(cat_df) == 0:
        continue
    _scatter.add_trace(go.Scatter(
        x=cat_df["avg_price"].to_list(), y=cat_df["sales_volume"].to_list(),
        mode="markers", name=cat.title(),
        marker=dict(color=PALETTE[i], size=7, opacity=0.65, line=dict(width=0)),
        customdata=list(zip(cat_df["brand"].to_list(), cat_df["product_id"].to_list())),
        hovertemplate="<b>%{customdata[0]}</b><br>Avg Price: $%{x:,.2f}<br>Sales: %{y:,}<extra>" + cat.title() + "</extra>",
    ))
_scatter.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=10, b=40),
    legend=dict(font=dict(color="#888", size=11), bgcolor="rgba(0,0,0,0)"),
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#555",
               tickprefix="$", title="Average Price (USD)", title_font=dict(color="#555", size=11)),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#555",
               title="Sales Volume (purchases)", title_font=dict(color="#555", size=11)),
    hoverlabel=dict(bgcolor="#1a1a2e", bordercolor="#00e5ff", font_color="#e0e0e0"),
)
SCATTER_JSON = _scatter.to_json()

STATS_LAYOUT = html.Div([
    html.Div([
        html.H2("Statistical Deep Dive"),
        html.P("Price distributions and product-level sales analysis"),
    ], className="page-header"),
    dbc.Row([
        dbc.Col(html.Div([html.Div("Avg Order Value", className="kpi-label"),
            html.Div(f"${_avg_order_val:,.2f}", className="kpi-value"),
            html.Div("mean purchase price", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),
        dbc.Col(html.Div([html.Div("Median Price", className="kpi-label"),
            html.Div(f"${_median_price:,.2f}", className="kpi-value text-purple"),
            html.Div("50th percentile", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),
        dbc.Col(html.Div([html.Div("Price Std Dev", className="kpi-label"),
            html.Div(f"${_price_std:,.2f}", className="kpi-value text-orange"),
            html.Div("price spread", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),
        dbc.Col(html.Div([html.Div("Priciest Brand", className="kpi-label"),
            html.Div(_top_brand.title(), className="kpi-value text-green", style={"fontSize": "1.4rem"}),
            html.Div("highest avg price", className="kpi-sub"),
        ], className="kpi-card"), xs=12, md=3),
    ], className="mb-4 g-3"),
    dbc.Row([dbc.Col(html.Div([
        html.Div(f"Price Distribution · Top 5 ({' · '.join(c.title() for c in _top5)})", className="section-title"),
        dcc.Graph(id="violin-graph", config={"displayModeBar": False}, style={"height": "360px"}),
    ], className="glass-card"), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(html.Div([
        html.Div("Price vs Sales Volume · Product Level", className="section-title"),
        dcc.Graph(id="scatter-graph", config={"displayModeBar": False}, style={"height": "380px"}),
    ], className="glass-card"), width=12)]),
    dcc.Store(id="violin-store",  data=VIOLIN_JSON),
    dcc.Store(id="scatter-store", data=SCATTER_JSON),
])

print("✅ Statistics figures ready.")

# ── App Initialization ─────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server
server.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

# ── Callbacks ──────────────────────────────────────────────────────────────────
@app.callback(Output("violin-graph",  "figure"), Input("violin-store",  "data"))
def load_violin(data):
    return go.Figure(pio.from_json(data))

@app.callback(Output("scatter-graph", "figure"), Input("scatter-store", "data"))
def load_scatter(data):
    return go.Figure(pio.from_json(data))

# ── Nav Items ──────────────────────────────────────────────────────────────────
NAV_ITEMS = [
    {"label": "Overview",   "href": "/",           "icon": "📊"},
    {"label": "Funnel",     "href": "/funnel",      "icon": "🔻"},
    {"label": "Geography",  "href": "/geography",   "icon": "🌍"},
    {"label": "Statistics", "href": "/statistics",  "icon": "📈"},
]

sidebar = html.Div(id="sidebar", children=[
    html.Div([
        html.Span("Ana",  style={"color": "#00e5ff"}),
        html.Span("-bro", style={"color": "#7b61ff"}),
    ], className="sidebar-logo"),
    html.Div("Navigation", className="sidebar-label"),
    *[
        dcc.Link(
            children=[html.Span(item["icon"], style={"fontSize": "1rem"}), html.Span(item["label"])],
            href=item["href"], className="nav-link", id=f"nav-{item['label'].lower()}",
        )
        for item in NAV_ITEMS
    ],
    html.Div([
        html.Div("Dataset", className="sidebar-label"),
        html.Div("2019-Oct.csv", style={"fontSize": "0.75rem", "color": "#444", "padding": "4px 8px"}),
    ], style={"marginTop": "auto"}),
])

app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(id="page-content", children=[dash.page_container]),
])

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050, threaded=True)