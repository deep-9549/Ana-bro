import dash
from dash import html

dash.register_page(__name__, path="/statistics", name="Statistics")

# Layout is pre-built once in app.py at server startup
# Importing it here means zero recomputation on every page visit
from app import STATS_LAYOUT

layout = STATS_LAYOUT