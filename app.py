import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from boiler import run_simulation, SHOWER_START_S, SHOWER_END_S


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout= html.Div(
    style={"maxWidth": "2000px", "margin": "0 auto", "fontFamily": "Arial", "marginBottom": "50px", "marginTop": "20px", "marginLeft": "100px", "marginRight": "50px"},
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
                dcc.Slider(id="slider-T-set", min=30, max=80, step=1, value=50, marks={i: str(i) for i in range(30, 81, 10)}, tooltip={"placement": "bottom", "always_visible": True},),
                html.Div(
                    dbc.Button(
                        "Zastosuj",
                        id="apply-button",
                        color="primary",
                        n_clicks=0,
                        size="lg",
                        style={"fontSize": "18px", "width": "220px", "height": "48px"},
                    ),
                    style={"textAlign": "center", "marginTop": "12px", "marginBottom": "12px"},
                ),
            ], width=6),
            dbc.Col([
                html.Br(),
                html.Label("Wzmocnienie proporcjonalne Kp"),
                dcc.Slider(
                    id="slider-Kp",
                    min=10,
                    max=1000,
                    step=5,
                    value=450,
                    marks={i: str(i) for i in range(0, 1001, 100)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),

                html.Br(),
                html.Label("Stała zdwojenia - Ti [s]"),
                dcc.Slider(
                    id="slider-Ti",
                    min=50,
                    max=5000,
                    step=50,
                    value=1200,
                    marks={i: str(i) for i in range(0, 5001, 500)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),

                html.Br(),
                html.Label("Czas wyprzedzenia - Td [s]"),
                dcc.Slider(
                    id="slider-Td",
                    min=0,
                    max=300,
                    step=5,
                    value=150,
                    marks={i: str(i) for i in range(0, 301, 50)},
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
        Input("apply-button", "n_clicks"),
    ],
    [
        State("slider-T-set", "value"),
        State("slider-Kp", "value"),
        State("slider-Ti", "value"),
        State("slider-Td", "value"),
        State("slider-volume", "value"),
    ]
)
def update_graph(n_clicks, T_set, Kp, Ti, Td, volume_type):
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
        rows=2, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.1,
        row_heights=[0.65, 0.35],
        subplot_titles=(
            f"Temperatura wody [°C]",
            "Bilans ciepła [kJ]"
        )
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["temperature"], name="Temperatura"),
        row=1, col=1
    )

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
        go.Scatter(
            x=df["time"],
            y=[float(T_set)] * len(df),
            mode="lines",
            name="Temperatura zadana",
            line=dict(color="red", dash="dash", width=2),
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["energy"], name="Ciepło oddane grzałki",
                   line=dict(color="purple")),
        row=2, col=1
    )
    if "energy_loss" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["time"], y=df["energy_loss"], name="Ciepło stracone do otoczenia",
                       line=dict(color="red",)),
            row=2, col=1
        )
    if "energy_draw" in df.columns:
        fig.add_trace(
            go.Scatter(x=df["time"], y=df["energy_draw"], name="Ciepło pobrane przez użytkownika",
                       line=dict(color="blue",)),
            row=2, col=1
        )

    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=1, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=2, col=1)

    fig.update_layout(
        height=1540,
        showlegend=True,
        margin=dict(l=0, r=40, t=40, b=40),
        legend=dict(
            font=dict(size=16),
            itemsizing='constant',
        ),
    )

    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="kJ", row=2, col=1)

    return fig


if __name__ == "__main__":
    app.run(debug=True)
