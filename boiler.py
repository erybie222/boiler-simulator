from dataclasses import dataclass
import pandas as pd


@dataclass
class BoilerParams:
    C: float
    k_loss: float
    k_draw: float
    T_out: float
    T_cold: float


def boiler_step(T: float,
                P_in: float,
                q_out: float,
                params: BoilerParams,
                dt: float) -> float:
    C = params.C
    k_loss = params.k_loss
    k_draw = params.k_draw
    T_out = params.T_out
    T_cold = params.T_cold

    P_loss = k_loss * (T - T_out)
    P_draw = k_draw * q_out * (T - T_cold)

    dTdt = (P_in - P_loss - P_draw) / C

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
    n = int(total_time / dt)

    T = params.T_cold

    time_hist = [0.0]
    T_hist = [T]
    P_hist = [0.0]
    q_hist = [0.0]
    P_term_hist = [0.0]
    I_term_hist = [0.0]
    D_term_hist = [0.0]

    integ = 0.0
    e_prev = T_set - T

    Ki = Kp / Ti if Ti > 0.0 else 0.0
    Kd = Kp * Td if Td > 0.0 else 0.0

    P_loss_estimated = params.k_loss * (T_set - params.T_out)
    integ_max = P_loss_estimated / Ki if Ki > 0.0 else float('inf')

    for k in range(n):
        t = (k + 1) * dt

        if callable(q_out_profile):
            q_out = q_out_profile(t)
        elif q_out_profile is None:
            q_out = 0.0
        else:
            q_out = float(q_out_profile)

        e = T_set - T

        P_term = Kp * e

        I_term = Ki * integ if Ki > 0.0 else 0.0

        D_term = Kd * (e - e_prev) / dt if Kd > 0.0 else 0.0

        u = P_term + I_term + D_term

        P_in = max(0.0, min(u, P_max))

        if Ki > 0.0:
            saturated_high = (P_in >= P_max) and (e > 0)
            saturated_low = (P_in <= 0) and (e < 0)

            if not (saturated_high or saturated_low):
                integ += e * dt

            if e < 5.0:
                scale = max(0.0, e / 5.0)
                current_limit = integ_max * (1.0 + scale)
                integ = max(-current_limit, min(integ, current_limit))

        e_prev = e

        T = boiler_step(T, P_in, q_out, params, dt)

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


params_default = BoilerParams(
    C=334_880.0,
    k_loss=5.0,
    k_draw=4186.0,
    T_out=22.0,
    T_cold=10.0,
)

DT = 1.0
TOTAL_TIME = 18000
P_MAX = 2000.0
FLOW_L_PER_MIN = 6.0
SHOWER_START_S = 10000.0
SHOWER_END_S = 12000.0


def q_out_profile_default(t: float) -> float:
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
) -> pd.DataFrame:
    C_dynamic = float(volume_l) * 4186.0

    V_ref = 80.0
    k_loss_ref = 5.0
    k_loss_dynamic = k_loss_ref * (float(volume_l) / V_ref) ** (2.0 / 3.0)

    params_dynamic = BoilerParams(
        C=C_dynamic,
        k_loss=k_loss_dynamic,
        k_draw=params_default.k_draw,
        T_out=params_default.T_out,
        T_cold=params_default.T_cold,
    )

    flow_lps = FLOW_L_PER_MIN / 60.0
    q_profile = make_q_out_profile(flow_lps, SHOWER_START_S, SHOWER_END_S)

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
