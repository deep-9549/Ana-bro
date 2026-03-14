import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.io as pio

# ── Global Plotly Theme ────────────────────────────────────────────────────────
pio.templates.default = "plotly_dark"

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

# ── Nav Items ─────────────────────────────────────────────────────────────────
NAV_ITEMS = [
    {"label": "Overview",        "href": "/",              "icon": "📊"},
    {"label": "Funnel",          "href": "/funnel",         "icon": "🔻"},
    {"label": "Geography",       "href": "/geography",      "icon": "🌍"},
    {"label": "Statistics",      "href": "/statistics",     "icon": "📈"},
]

# ── Sidebar ────────────────────────────────────────────────────────────────────
sidebar = html.Div(
    id="sidebar",
    children=[
        # Logo
        html.Div([
            html.Span("Ana", style={"color": "#00e5ff"}),
            html.Span("-bro", style={"color": "#7b61ff"}),
        ], className="sidebar-logo"),

        # Nav label
        html.Div("Navigation", className="sidebar-label"),

        # Nav links
        *[
            dcc.Link(
                children=[
                    html.Span(item["icon"], style={"fontSize": "1rem"}),
                    html.Span(item["label"]),
                ],
                href=item["href"],
                className="nav-link",
                id=f"nav-{item['label'].lower()}",
            )
            for item in NAV_ITEMS
        ],

        # Bottom info
        html.Div(
            [
                html.Div("Dataset", className="sidebar-label"),
                html.Div("2019-Oct.csv", style={
                    "fontSize": "0.75rem",
                    "color": "#444",
                    "padding": "4px 8px",
                }),
            ],
            style={"marginTop": "auto"},
        ),
    ],
)

# ── Root Layout ────────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(
        id="page-content",
        children=[dash.page_container],
    ),
])

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050)