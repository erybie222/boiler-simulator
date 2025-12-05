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
    P_term_hist = [0.0]
    I_term_hist = [0.0]
    D_term_hist = [0.0]

    integ = 0.0  # całka błędu
    e_prev = T_set - T  # początkowy błąd (aby D_term nie był ogromny w pierwszym kroku)

    # Oblicz Ki raz na początku
    Ki = Kp / Ti if Ti > 0.0 else 0.0
    Kd = Kp * Td if Td > 0.0 else 0.0

    # Maksymalna wartość całki - ogranicza I_term
    # Szacowane straty ciepła przy T_set: k_loss * (T_set - T_out)
    # Człon I powinien kompensować straty w stanie ustalonym
    P_loss_estimated = params.k_loss * (T_set - params.T_out)
    # I_term_max = P_loss_estimated (bez marginesu, aby nie było overshootu)
    integ_max = P_loss_estimated / Ki if Ki > 0.0 else float('inf')

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

        # --- człon I (całkujący) z aktualną całką ---
        I_term = Ki * integ if Ki > 0.0 else 0.0

        # --- człon D (różniczkujący) ---
        D_term = Kd * (e - e_prev) / dt if Kd > 0.0 else 0.0

        # --- wyjście PID (przed nasyceniem) ---
        u = P_term + I_term + D_term

        # --- nasycenie (ograniczenie mocy grzałki) ---
        P_in = max(0.0, min(u, P_max))

        # --- ANTI-WINDUP: clamping ---
        # Nie akumuluj całki gdy:
        # - wyjście nasycone na górze (P_in >= P_max) i błąd dodatni (e > 0, chcemy grzać więcej)
        # - wyjście nasycone na dole (P_in <= 0) i błąd ujemny (e < 0, chcemy grzać mniej)
        if Ki > 0.0:
            saturated_high = (P_in >= P_max) and (e > 0)
            saturated_low = (P_in <= 0) and (e < 0)

            if not (saturated_high or saturated_low):
                integ += e * dt

            # Dynamiczne ograniczenie całki - aktywne tylko gdy blisko setpoint
            # Gdy T jest daleko od T_set, pozwól całce rosnąć normalnie
            # Gdy T zbliża się do T_set, ogranicz całkę proporcjonalnie
            if e < 5.0:  # Gdy błąd < 5°C (blisko setpoint)
                # Oblicz dynamiczny limit: pełne ograniczenie gdy e=0, brak gdy e>=5
                scale = max(0.0, e / 5.0)  # 0.0 gdy e=0, 1.0 gdy e>=5
                current_limit = integ_max * (1.0 + scale)  # od 1x do 2x strat
                integ = max(-current_limit, min(integ, current_limit))

        # zapamiętaj błąd dla następnej iteracji
        e_prev = e

        # --- fizyka bojlera (jeden krok) ---
        T = boiler_step(T, P_in, q_out, params, dt)

        # --- logowanie ---
        time_hist.append(t)
        T_hist.append(T)
        P_hist.append(P_in)
        q_hist.append(q_out)
        P_term_hist.append(P_term)
        I_term_hist.append(I_term)
        D_term_hist.append(D_term)

    return pd.DataFrame({
        "time": time_hist,
        "temperature": T_hist,
        "power": P_hist,
        "q_out": q_hist,
        "P_term": P_term_hist,
        "I_term": I_term_hist,
        "D_term": D_term_hist,
    })

# Parametry dla bojlera 80L:
# C = 80 kg * 4186 J/(kg·°C) ≈ 334880 J/°C
# Grzałka: 2000W (typowa dla średnich bojlerów)
params_default = BoilerParams(
    C=334_880.0,       # pojemność cieplna dla 80L wody
    k_loss=5.0,        # straty ciepła do otoczenia [W/°C] - dobrze izolowany bojler
    k_draw=4186.0,     # współczynnik chłodzenia przy poborze [W/(°C·l/s)] = c_p wody
    T_out=22.0,        # temperatura otoczenia [°C]
    T_cold=10.0,       # temperatura zimnej wody z sieci [°C]
)

DT = 1.0
TOTAL_TIME = 18000  # 2 godziny symulacji
P_MAX = 2000.0


def q_out_profile_default(t: float) -> float:
    # prosty prysznic: od 600s do 1800s pobór 0.1 l/s
    if 600 <= t <= 1800:
        return 0.1
    return 0.0


def make_q_out_profile(flow_lps: float, start_s: float, end_s: float):
    def _profile(t: float) -> float:
        if start_s <= t <= end_s:
            return flow_lps
        return 0.0
    return _profile


def run_simulation(
    T_set: float,
    Kp: float,
    Ti: float,
    Td: float = 0.0,
    P_max: float = P_MAX,
    volume_l: float = 50.0,
    flow_l_per_min: float = 6.0,
    shower_start_s: float = 10000.0,
    shower_end_s: float = 12000.0,
) -> pd.DataFrame:
    # Przelicz pojemność cieplną wody na podstawie objętości [L]
    # Zakładamy gęstość ~1 kg/L oraz ciepło właściwe wody ~4186 J/(kg·°C)
    C_dynamic = float(volume_l) * 4186.0

    # Dynamiczne k_loss - straty ciepła zależą od powierzchni bojlera
    # Powierzchnia rośnie proporcjonalnie do V^(2/3)
    # Dla bojlera referencyjnego 80L przyjmujemy k_loss = 5.0 W/°C
    # k_loss = k_loss_ref * (V / V_ref)^(2/3)
    V_ref = 80.0  # objętość referencyjna [L]
    k_loss_ref = 5.0  # straty dla bojlera 80L [W/°C]
    k_loss_dynamic = k_loss_ref * (float(volume_l) / V_ref) ** (2.0 / 3.0)

    params_dynamic = BoilerParams(
        C=C_dynamic,
        k_loss=k_loss_dynamic,
        k_draw=params_default.k_draw,
        T_out=params_default.T_out,
        T_cold=params_default.T_cold,
    )

    # Zbuduj profil poboru na podstawie parametrów UI (l/min → l/s)
    flow_lps = float(flow_l_per_min) / 60.0
    q_profile = make_q_out_profile(flow_lps, float(shower_start_s), float(shower_end_s))

    return simulate_boiler_pid(
        T_set=T_set,
        Kp=Kp,
        Ti=Ti,
        Td=Td,
        params=params_dynamic,
        dt=DT,
        total_time=TOTAL_TIME,
        P_max=P_max,
        q_out_profile=q_profile,
    )


