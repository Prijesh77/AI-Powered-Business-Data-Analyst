"""Plotly charts built directly from analytics tables.

Each function draws exactly the table it is given (no re-calculation), so a
chart always matches the table shown next to it.

Style rules: one hue per single-series chart (no legend needed), partial periods
marked by pattern and label as well as a lighter shade, one y-axis only,
thin marks, a recessive grid, and hover tooltips with exact values.
"""

import pandas as pd
import plotly.graph_objects as go

PRIMARY = "#2F6FDB"      # single-series hue (mid blue, readable on light and dark backgrounds)
MUTED = "#9AA5B4"        # de-emphasised marks (partial periods, non-revenue lines)
GRID = "rgba(128,128,128,0.18)"

PERIOD_LABELS = {"day": "Day", "week": "Week starting", "month": "Month"}


def _base_layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 16}},
        height=height,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"font_size": 13},
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID)
    return fig


def money_format(currency: str) -> str:
    return f"{currency} " if currency else ""


def sales_trend(trend: pd.DataFrame, freq: str, currency: str = "") -> go.Figure:
    """Net sales per period from breakdowns.sales_over_time()."""
    prefix = money_format(currency)
    complete = trend.loc[~trend["is_partial"]]
    partial = trend.loc[trend["is_partial"]]
    x_label = PERIOD_LABELS.get(freq, "Period")
    hover = (f"%{{customdata[0]}}<br>Net sales: {prefix}%{{y:,.2f}}"
             "<br>Orders: %{customdata[1]:,}<extra>%{customdata[2]}</extra>")

    def custom(frame: pd.DataFrame, note: str):
        return list(zip(frame["period"], frame["orders"], [note] * len(frame)))

    fig = go.Figure()
    if freq == "month":
        fig.add_bar(x=complete["period_start"], y=complete["net_sales"], name="Complete period",
                    marker={"color": PRIMARY, "cornerradius": 4},
                    customdata=custom(complete, ""), hovertemplate=hover)
        fig.add_bar(x=partial["period_start"], y=partial["net_sales"], name="Partial period",
                    marker={"color": MUTED, "pattern": {"shape": "/"}, "cornerradius": 4},
                    customdata=custom(partial, "partial period"), hovertemplate=hover)
        fig.update_xaxes(dtick="M3", tickformat="%b %Y")
    else:
        fig.add_scatter(x=trend["period_start"], y=trend["net_sales"], mode="lines",
                        line={"color": PRIMARY, "width": 2}, name="Net sales",
                        customdata=custom(trend, ""), hovertemplate=hover)
        fig.add_scatter(x=partial["period_start"], y=partial["net_sales"], mode="markers",
                        marker={"color": "rgba(0,0,0,0)", "size": 10,
                                "line": {"color": PRIMARY, "width": 2}},
                        name="Partial period", customdata=custom(partial, "partial period"),
                        hovertemplate=hover)
    fig.update_layout(showlegend=not partial.empty,
                      legend={"orientation": "h", "y": 1.02, "x": 1, "xanchor": "right", "yanchor": "bottom"},
                      hovermode="closest")
    fig.update_yaxes(title=f"Net sales ({currency})" if currency else "Net sales", tickformat=",.0f")
    fig.update_xaxes(title=x_label)
    return _base_layout(fig, f"Net sales by {freq}")


def ranking_bar(table: pd.DataFrame, label_column: str, value_column: str, title: str,
                currency: str = "", value_name: str = "Net sales") -> go.Figure:
    """Horizontal bars, largest at the top, each labelled with its value."""
    prefix = money_format(currency) if value_column.endswith("sales") else ""
    ordered = table.iloc[::-1]  # Plotly draws the first row at the bottom
    labels = ordered[label_column].astype(str).str.slice(0, 40)
    fig = go.Figure(go.Bar(
        x=ordered[value_column], y=labels, orientation="h",
        marker={"color": PRIMARY, "cornerradius": 4},
        text=[f"{prefix}{v:,.0f}" for v in ordered[value_column]],
        textposition="outside", cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{value_name}: {prefix}%{{x:,.2f}}<extra></extra>",
    ))
    fig.update_xaxes(title=value_name, tickformat=",.0f", showgrid=True, gridcolor=GRID)
    # Labels are names, never numbers: IDs such as "18102" must not become a numeric axis.
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)", type="category")
    return _base_layout(fig, title, height=max(260, 34 * len(table) + 90))


def line_type_bar(summary: pd.DataFrame) -> go.Figure:
    """Number of lines per line type; revenue types highlighted, others muted."""
    ordered = summary.iloc[::-1]
    fig = go.Figure()
    for counts, name, color in ((True, "Counts towards revenue", PRIMARY), (False, "Excluded from revenue", MUTED)):
        part = ordered.loc[ordered["counts_in_revenue"] == counts]
        fig.add_bar(x=part["lines"], y=part["line_type"], orientation="h", name=name,
                    marker={"color": color, "cornerradius": 4},
                    text=[f"{v:,}" for v in part["lines"]], textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>Lines: %{x:,}<extra>" + name + "</extra>")
    fig.update_layout(legend={"orientation": "h", "y": 1.02, "x": 1, "xanchor": "right", "yanchor": "bottom"})
    fig.update_xaxes(title="Lines (log scale)", type="log")
    fig.update_yaxes(categoryorder="array", categoryarray=ordered["line_type"].tolist())
    return _base_layout(fig, "Rows by line type", height=320)
