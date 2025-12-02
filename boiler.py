from dataclasses import dataclass
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import dash
from dash import dcc, html
from dash.dependencies import Input, Output


@dataclass
class BoilerParams:
    C: float        # [J/°C] - pojemność cieplna wody/bojlera
    k_loss: float   # [W/°C] - straty ciepła do otoczenia
    k_draw: float   # [W/(°C·(l/s))] - "siła" chłodzenia przy poborze
    T_out: float    # [°C] - temperatura otoczenia (łazienka)
    T_cold: float   # [°C] - temperatura zimnej wody z sieci


def boiler_step(T: float,
                P_in: float,
                q_out: float,
                params: BoilerParams,
                dt: float) -> float:
    """
    Jeden krok symulacji bojlera.

    T      - aktualna temperatura wody [°C]
    P_in   - moc grzałki w tym kroku [W] (sterowanie od regulatora / stała)
    q_out  - przepływ ciepłej wody [l/s] (zakłócenie, np. prysznic)
    params - parametry bojlera (C, k_loss, k_draw, T_out, T_cold)
    dt     - krok czasowy [s]
    """
    C = params.C
    k_loss = params.k_loss
    k_draw = params.k_draw
    T_out = params.T_out
    T_cold = params.T_cold

    # bilans mocy (W)
    P_loss = k_loss * (T - T_out)
    P_draw = k_draw * q_out * (T - T_cold)

    # dT/dt
    dTdt = (P_in - P_loss - P_draw) / C

    # Euler
    T_next = T + dt * dTdt
    return T_next


def simulate_boiler_pi(
    T_set: float,
    Kp: float,
    Ti: float,
    params: BoilerParams,
    dt: float,
    total_time: float,
    P_max: float,
    q_out_profile=None,  # funkcja lub stała; na start może być 0
) -> pd.DataFrame:
    """
    Symulacja bojlera z regulatorem PI.
    Zwraca DataFrame: time, temperature, power, q_out.
    """
    n = int(total_time / dt)

    # stan początkowy: np. zimna woda z sieci
    T = params.T_cold

    time_hist = [0.0]
    T_hist = [T]
    P_hist = [0.0]
    q_hist = [0.0]

    integ = 0.0  # całka błędu

    for k in range(n):
        t = (k + 1) * dt

        # --- profil poboru wody q_out(t) ---
        if callable(q_out_profile):
            q_out = q_out_profile(t)
        elif q_out_profile is None:
            q_out = 0.0  # brak poboru
        else:
            q_out = float(q_out_profile)  # stała wartość

        # --- błąd temperatury ---
        e = T_set - T

        # --- anti-windup: przewidywane sterowanie przed nasyceniem ---
        if Ti > 0.0:
            will_integ = True
            u_pred = Kp * (e + integ / Ti)

            if u_pred >= P_max and e > 0:
                will_integ = False
            if u_pred <= 0.0 and e < 0:
                will_integ = False

            if will_integ:
                integ += e * dt

        # --- wyjście PI + nasycenie ---
        if Ti > 0.0:
            u = Kp * (e + integ / Ti)
        else:
            u = Kp * e  # czysty P, gdyby Ti==0

        P_in = max(0.0, min(u, P_max))

        # --- fizyka bojlera (jeden krok) ---
        T = boiler_step(T, P_in, q_out, params, dt)

        # --- logowanie ---
        time_hist.append(t)
        T_hist.append(T)
        P_hist.append(P_in)
        q_hist.append(q_out)

    return pd.DataFrame({
        "time": time_hist,
        "temperature": T_hist,
        "power": P_hist,
        "q_out": q_hist,
    })

params_default = BoilerParams(
    C=400_000.0,
    k_loss=15.0,
    k_draw=3_000.0,
    T_out=22.0,
    T_cold=10.0,
)

DT = 1.0
TOTAL_TIME = 3600
P_MAX = 2000.0


def q_out_profile_default(t: float) -> float:
    # prosty prysznic: od 600s do 1800s pobór 0.1 l/s
    if 600 <= t <= 1800:
        return 0.1
    return 0.0


def run_simulation(T_set: float, Kp: float, Ti: float) -> pd.DataFrame:
    return simulate_boiler_pi(
        T_set=T_set,
        Kp=Kp,
        Ti=Ti,
        params=params_default,
        dt=DT,
        total_time=TOTAL_TIME,
        P_max=P_MAX,
        q_out_profile=q_out_profile_default,
    )


app = dash.Dash(__name__)

app.layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "fontFamily": "Arial"},
    children=[
        html.H1("Symulacja bojlera", style={"textAlign": "center"}),

        html.Div([
            html.Label("T[°C]"),
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
            html.Label("Kp"),
            dcc.Slider(
                id="slider-Kp",
                min=0.5,
                max=10.0,
                step=0.1,
                value=2.0,
                marks={i: str(i) for i in range(1, 11)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),

            html.Br(),
            html.Label("Ti[s]"),
            dcc.Slider(
                id="slider-Ti",
                min=0,
                max=2000,
                step=50,
                value=600,
                marks={0: "0", 600: "600", 1200: "1200", 2000: "2000"},
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
    ]
)
def update_graph(T_set, Kp, Ti):
    df = run_simulation(T_set=float(T_set), Kp=float(Kp), Ti=float(Ti))

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

