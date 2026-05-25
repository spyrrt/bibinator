import plotly.graph_objects as go

COLORS = ["#3b82f6", "#f59e06", "#10b981", "#8b5cf6", 
          "#ec4899", "#06b6d4", "#f97316", "#84cc16"]


PLOTLY_TEMPLATE = dict(
    layout = dict(
        paper_bgcolor = "#0f1117",
        plot_bgcolor = "#0f1117",
        font = dict(family = "IBM Plex Mono, monospace", color = "#c9d1d9", size = 11),
        xaxis = dict (gridcolor = "#2a2d3a", linecolor = "#2a2d3a", tickcolor = "#6b7280"),
        yaxis = dict (gridcolor = "#2a2d3a", linecolor = "#2a2d3a", tickcolor = "#6b7280"),
        legend = dict(bgcolor = "#1a1d2e", bordercolor = "#2a2d3a", borderwidth = 1),
        colorway = COLORS,
    )
)

def apply_custom_theme(fig):
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig