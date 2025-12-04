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


def simulate_boiler_pid(
    T_set: float,
    Kp: float,
    Ti: float,
    Td: float,
    params: BoilerParams,
    dt: float,
    total_time: float,
    P_max: float,
    q_out_profile=None,
) -> pd.DataFrame:
    """
    Symulacja bojlera z regulatorem PID.
    Zwraca DataFrame: time, temperature, power, q_out.

    Równania regulatora PID:
    u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt
    gdzie: Ki = Kp/Ti, Kd = Kp*Td
    """
    n = int(total_time / dt)

    # stan początkowy: np. zimna woda z sieci
    T = params.T_cold

    time_hist = [0.0]
    T_hist = [T]
    P_hist = [0.0]
    q_hist = [0.0]

    integ = 0.0  # całka błędu
    e_prev = 0.0  # poprzedni błąd (dla członu D)

    for k in range(n):
        t = (k + 1) * dt

        if callable(q_out_profile):
            q_out = q_out_profile(t)
        elif q_out_profile is None:
            q_out = 0.0
        else:
            q_out = float(q_out_profile)

        # błąd regulacji
        e = T_set - T

        # --- człon P (proporcjonalny) ---
        P_term = Kp * e

        # --- człon I (całkujący) z anti-windup ---
        # Anti-windup: nie całkuj gdy sterowanie jest nasycone
        if Ti > 0.0:
            Ki = Kp / Ti
            # Sprawdź czy sterowanie będzie nasycone
            u_test = Kp * e + Ki * integ
            if 0.0 < u_test < P_max:
                # Brak nasycenia - normalnie całkuj
                integ += e * dt
            elif u_test >= P_max and e < 0:
                # Nasycenie górne, ale błąd ujemny - całkuj (pomaga zejść)
                integ += e * dt
            elif u_test <= 0.0 and e > 0:
                # Nasycenie dolne, ale błąd dodatni - całkuj (pomaga wyjść)
                integ += e * dt
            I_term = Ki * integ
        else:
            I_term = 0.0

        # --- człon D (różniczkujący) ---
        if Td > 0.0:
            Kd = Kp * Td
            D_term = Kd * (e - e_prev) / dt
        else:
            D_term = 0.0

        # --- wyjście PID ---
        u = P_term + I_term + D_term

        # --- nasycenie (ograniczenie mocy grzałki) ---
        P_in = max(0.0, min(u, P_max))

        # zapamiętaj błąd dla następnej iteracji
        e_prev = e

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

# Parametry dla bojlera 50L:
# C = 50 kg * 4186 J/(kg·°C) ≈ 209300 J/°C
# Grzałka: 2000W (typowa dla małych bojlerów)
params_default = BoilerParams(
    C=209_300.0,       # pojemność cieplna dla 50L wody
    k_loss=5.0,        # straty ciepła do otoczenia (izolacja)
    k_draw=4_186.0,    # ~c_wody * 1 kg/s przy przepływie 1 l/s
    T_out=22.0,        # temperatura otoczenia
    T_cold=10.0,       # temperatura zimnej wody
)

DT = 1.0
TOTAL_TIME = 18000  # 2 godziny symulacji
P_MAX = 2000.0


def q_out_profile_default(t: float) -> float:
    # prosty prysznic: od 600s do 1800s pobór 0.1 l/s
    if 600 <= t <= 1800:
        return 0.1
    return 0.0


def run_simulation(T_set: float, Kp: float, Ti: float, Td: float = 0.0) -> pd.DataFrame:
    return simulate_boiler_pid(
        T_set=T_set,
        Kp=Kp,
        Ti=Ti,
        Td=Td,
        params=params_default,
        dt=DT,
        total_time=TOTAL_TIME,
        P_max=P_MAX,
        q_out_profile=q_out_profile_default,
    )


