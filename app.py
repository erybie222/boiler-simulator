import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from boiler import run_simulation


app = dash.Dash(__name__)

app.layout = html.Div(
    style={"maxWidth": "2000px", "margin": "0 auto", "fontFamily": "Arial"},
    children=[
        html.H1("Symulacja bojlera", style={"textAlign": "center"}),

        html.Div([
            html.Label("Temperatura zadana wody w bojlerze - T[°C]"),
            dcc.Slider(
                id="slider-T-set",
                min=30,
                max=70,
                step=1,
                value=50,
                marks={i: str(i) for i in range(30, 71, 10)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

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
            html.Label("Czas całkowania  - Ti [s]"),
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
            html.Label("Czas różniczkowania - Td[s]"),
            dcc.Slider(
                id="slider-Td",
                min=0,
                max=60,
                step=5,
                value=15,
                marks={i: str(i) for i in range(0, 61, 10)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Maksymalna moc grzałki - P_max [W]"),
            dcc.Slider(
                id="slider-Pmax",
                min=1000,
                max=4000,
                step=250,
                value=2000,
                marks={i: str(i) for i in range(1000, 4001, 500)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Pojemność bojlera - V[L]"),
            dcc.Slider(
                id="slider-volume",
                min=30,
                max=150,
                step=10,
                value=80,
                marks={i: str(i) for i in range(30, 151, 30)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Przepływ wody podczas poboru [l/min]"),
            dcc.Slider(
                id="slider-qout-lpm",
                min=0,
                max=15,
                step=0.5,
                value=6.0,
                marks={i: str(i) for i in range(0, 16, 3)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Przedział czasowy poboru wody [s]"),
            dcc.RangeSlider(
                id="slider-shower-time",
                min=0,
                max=18000,
                step=100,
                value=[10000, 12000],
                marks={i: str(i) for i in range(0, 18001, 3000)},
                tooltip={"placement": "bottom", "always_visible": True},
                allowCross=False,
            ),
        ], style={"marginBottom": "50px"}),

        dcc.Graph(
            id="boiler-graph",
            style={"height": "1800px"},
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
        Input("slider-shower-time", "value"),
    ]
)
def update_graph(T_set, Kp, Ti, Td, Pmax, volume, qout_lpm, shower_time):
    shower_start = shower_time[0] if shower_time else 10000
    shower_end = shower_time[1] if shower_time else 12000

    df = run_simulation(
        T_set=float(T_set),
        Kp=float(Kp),
        Ti=float(Ti),
        Td=float(Td),
        P_max=float(Pmax),
        volume_l=float(volume),
        flow_l_per_min=float(qout_lpm),
        shower_start_s=float(shower_start),
        shower_end_s=float(shower_end),
    )

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=False,
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

    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=1, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=2, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=3, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=4, col=1)

    fig.update_layout(
        height=2200,
        showlegend=True,
        margin=dict(l=60, r=40, t=40, b=40),
        legend=dict(
            font=dict(size=16),
            itemsizing='constant',
        ),
    )

    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="W", row=2, col=1)
    fig.update_yaxes(title_text="W", row=3, col=1)
    fig.update_yaxes(title_text="l/s", row=4, col=1)

    return fig


if __name__ == "__main__":
    app.run(debug=True)
