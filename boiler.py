from dataclasses import dataclass
import pandas as pd

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

