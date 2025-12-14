import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from boiler import run_simulation, SHOWER_START_S, SHOWER_END_S


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout= html.Div(
    style={"maxWidth": "2000px", "margin": "0 auto", "fontFamily": "Arial", "marginBottom": "50px"},
    children=[
        html.H1("Symulacja bojlera", style={"textAlign": "center"}),
        dbc.Row([
            dbc.Col([
                html.Br(),
                html.Label('Rodzaj bojlera'),
                dcc.Dropdown(options=[
                    {"label": "Mały (50l, 2000W)", "value": "small"},
                    {"label": "Średni (80l, 3000W)", "value": "medium"},
                    {"label": "Duży (120l, 3500W)", "value": "large"},],
                    id="slider-volume",
                    value="medium",
                    clearable=False,
                    searchable=False,
                    style={"marginBottom": "50px"},
                ),
                html.Label("Temperatura zadana wody w bojlerze - T[°C]"),
                dcc.Slider(id="slider-T-set", min=30, max=70, step=1, value=50, marks={i: str(i) for i in range(30, 71, 10)}, tooltip={"placement": "bottom", "always_visible": True},),
            ], width=6),
            dbc.Col([
                html.Br(),
                html.Label("Wzmocnienie proporcjonalne Kp"),
                dcc.Slider(
                    id="slider-Kp",
                    min=10,
                    max=300,
                    step=10,
                    value=80,
                    marks={i: str(i) for i in range(0, 301, 50)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),

                html.Br(),
                html.Label("Stała zdwojenia - Ti [s]"),
                dcc.Slider(
                    id="slider-Ti",
                    min=50,
                    max=1500,
                    step=50,
                    value=400,
                    marks={i: str(i) for i in range(0, 1501, 300)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),

                html.Br(),
                html.Label("Stała wyprzedzenia - Td [s]"),
                dcc.Slider(
                    id="slider-Td",
                    min=0,
                    max=60,
                    step=5,
                    value=15,
                    marks={i: str(i) for i in range(0, 61, 10)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),

            ], width=6),
        ]),
        dbc.Row(dcc.Graph(
            id="boiler-graph",
            style={"height": "1260px"},
            config={"responsive": True}
        ),)
    ]
)

@app.callback(
    Output("boiler-graph", "figure"),
    [
        Input("slider-T-set", "value"),
        Input("slider-Kp", "value"),
        Input("slider-Ti", "value"),
        Input("slider-Td", "value"),
        Input("slider-volume", "value"),
    ]
)
def update_graph(T_set, Kp, Ti, Td, volume_type):
    volume_map = {
        "small": (50.0, 2000.0),
        "medium": (80.0, 3000.0),
        "large": (120.0, 3500.0),
    }
    volume, P_max = volume_map.get(volume_type, (80.0, 3000.0))

    df = run_simulation(
        T_set=float(T_set),
        Kp=float(Kp),
        Ti=float(Ti),
        Td=float(Td),
        P_max=float(P_max),
        volume_l=float(volume),
    )

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.06,
        row_heights=[0.4, 0.35, 0.25],
        subplot_titles=(
            f"Temperatura wody [°C]",
            "Składowe PID [W]",
            "Ciepło grzałki [kJ]"
        )
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["temperature"], name="Temperatura"),
        row=1, col=1
    )

    # Pionowe przerywane linie pokazujące początek i koniec poboru wody
    temp_min = df["temperature"].min()
    temp_max = df["temperature"].max()
    fig.add_trace(
        go.Scatter(
            x=[SHOWER_START_S, SHOWER_START_S],
            y=[temp_min, temp_max],
            mode="lines",
            name="Początek poboru",
            line=dict(color="orange", dash="dash", width=2),
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=[SHOWER_END_S, SHOWER_END_S],
            y=[temp_min, temp_max],
            mode="lines",
            name="Koniec poboru",
            line=dict(color="orange", dash="dash", width=2),
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["P_term"], name="P (proporcjonalny)",
                   line=dict(color="red")),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["I_term"], name="I (całkujący)",
                   line=dict(color="green")),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["D_term"], name="D (różniczkujący)",
                   line=dict(color="blue")),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["energy"], name="Ciepło grzałki",
                   line=dict(color="purple")),
        row=3, col=1
    )

    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=1, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=2, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=3, col=1)

    fig.update_layout(
        height=1540,
        showlegend=True,
        margin=dict(l=60, r=40, t=40, b=40),
        legend=dict(
            font=dict(size=16),
            itemsizing='constant',
        ),
    )

    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="W", row=2, col=1)
    fig.update_yaxes(title_text="kJ", row=3, col=1)

    return fig


if __name__ == "__main__":
    app.run(debug=True)
