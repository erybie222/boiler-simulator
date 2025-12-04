import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from boiler import run_simulation


app = dash.Dash(__name__)

app.layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "fontFamily": "Arial"},
    children=[
        html.H1("Symulacja bojlera", style={"textAlign": "center"}),

        html.Div([
            html.Label("Temperatura zadana wody w bojlerze - T[°C]"),
            dcc.Slider(
                id="slider-T-set",
                min=30,
                max=70,
                step=1,
                value=45,
                marks={i: str(i) for i in range(30, 71, 5)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Wzmocnienie regulatora - Kp"),
            dcc.Slider(
                id="slider-Kp",
                min=10,
                max=200,
                step=5,
                value=100,
                marks={i: str(i) for i in range(0, 201, 50)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Stała całkowania - Ti[s]"),
            dcc.Slider(
                id="slider-Ti",
                min=0,
                max=2000,
                step=50,
                value=600,
                marks={0: "0", 600: "600", 1200: "1200", 2000: "2000"},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Czas różniczkowania - Td[s]"),
            dcc.Slider(
                id="slider-Td",
                min=0,
                max=100,
                step=5,
                value=0,
                marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"},
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ], style={"marginBottom": "40px"}),

        dcc.Graph(id="boiler-graph", style={"height": "900px"}),
    ]
)


@app.callback(
    Output("boiler-graph", "figure"),
    [
        Input("slider-T-set", "value"),
        Input("slider-Kp", "value"),
        Input("slider-Ti", "value"),
        Input("slider-Td", "value"),
    ]
)
def update_graph(T_set, Kp, Ti, Td):
    df = run_simulation(T_set=float(T_set), Kp=float(Kp), Ti=float(Ti), Td=float(Td))

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            f"Temperatura wody [°C]",
            "Moc grzałki [W]",
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
        go.Scatter(x=df["time"], y=df["q_out"], name="Pobór wody"),
        row=3, col=1
    )

    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=1, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=2, col=1)
    fig.update_xaxes(title_text="czas [s]", showticklabels=True, row=3, col=1)

    return fig


if __name__ == "__main__":
    app.run(debug=True)

