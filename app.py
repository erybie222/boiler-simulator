import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from boiler import run_simulation


app = dash.Dash(__name__)

app.layout = html.Div(
    style={"maxWidth": "1400px", "margin": "0 auto", "fontFamily": "Arial"},
    children=[
        html.H1("Symulacja bojlera", style={"textAlign": "center"}),

        html.Div([
            html.Label("Temperatura zadana wody w bojlerze - T[°C]"),
            dcc.Slider(
                id="slider-T-set",
                min=30,
                max=70,
                step=1,
                value=55,
                marks={i: str(i) for i in range(30, 71, 5)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Wzmocnienie regulatora - Kp"),
            dcc.Slider(
                id="slider-Kp",
                min=1,
                max=500,
                step=5,
                value=100,
                marks={i: str(i) for i in range(0, 501, 100)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Stała całkowania - Ti[s]"),
            dcc.Slider(
                id="slider-Ti",
                min=10,
                max=2000,
                step=50,
                value=500,
                marks={i: str(i) for i in range(0, 2001, 400)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Czas różniczkowania - Td[s]"),
            dcc.Slider(
                id="slider-Td",
                min=0,
                max=100,
                step=5,
                value=50,
                marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Maksymalna moc grzałki - Pmax[W]"),
            dcc.Slider(
                id="slider-Pmax",
                min=1500,
                max=4000,
                step=100,
                value=2000,
                marks={i: str(i) for i in range(1500, 4001, 500)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Pojemność bojlera - V[L]"),
            dcc.Slider(
                id="slider-volume",
                min=30,
                max=150,
                step=5,
                value=80,
                marks={i: str(i) for i in range(30, 151, 20)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Pobór ciepłej wody - q [l/min]"),
            dcc.Slider(
                id="slider-qout-lpm",
                min=0,
                max=20,
                step=0.5,
                value=8.0,
                marks={i: str(i) for i in range(0, 21, 5)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ], style={"marginBottom": "40px"}),

        dcc.Graph(
            id="boiler-graph",
            style={"height": "1400px"},
            config={"responsive": True}
        ),
    ]
)


@app.callback(
    Output("boiler-graph", "figure"),
    [
        Input("slider-T-set", "value"),
        Input("slider-Kp", "value"),
        Input("slider-Ti", "value"),
        Input("slider-Td", "value"),
        Input("slider-Pmax", "value"),
        Input("slider-volume", "value"),
        Input("slider-qout-lpm", "value"),
    ]
)
def update_graph(T_set, Kp, Ti, Td, Pmax, volume, qout_lpm):
    df = run_simulation(
        T_set=float(T_set),
        Kp=float(Kp),
        Ti=float(Ti),
        Td=float(Td),
        P_max=float(Pmax),
        volume_l=float(volume),
        flow_l_per_min=float(qout_lpm),
    )

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.3, 0.25, 0.25, 0.2],
        subplot_titles=(
            f"Temperatura wody [°C]",
            "Moc grzałki [W]",
            "Składowe PID [W]",
            "Pobór wody [l/s]"
        )
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["temperature"], name="Temperatura"),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["power"], name="Moc grzałki"),
        row=2, col=1
    )

    # Składowe PID
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["P_term"], name="P (proporcjonalny)",
                   line=dict(color="red")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["I_term"], name="I (całkujący)",
                   line=dict(color="green")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df["time"], y=df["D_term"], name="D (różniczkujący)",
                   line=dict(color="blue")),
        row=3, col=1
    )

    fig.add_trace(
        go.Scatter(x=df["time"], y=df["q_out"], name="Pobór wody"),
        row=4, col=1
    )

    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=4, col=1)
    fig.update_layout(
        height=1400,
        showlegend=True,
        margin=dict(l=60, r=40, t=40, b=40),
    )

    # Ustaw zakres Y dla każdego wykresu osobno
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="W", row=2, col=1)
    fig.update_yaxes(title_text="W", row=3, col=1)
    fig.update_yaxes(title_text="l/s", row=4, col=1)

    return fig


if __name__ == "__main__":
    app.run(debug=True)

