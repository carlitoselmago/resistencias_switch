import numpy as np
from scipy.optimize import curve_fit


class temp:
    def __init__(self):
        pass

    # --------------------------------
    # RUNTIME MODEL (PER SECOND STEP)
    # --------------------------------
    def update_temperature(
        self,
        T_prev: float,
        is_on: bool,
        T_ambient: float,
        T_max: float,
        alpha_on_1s: float,
        alpha_off_1s: float
    ) -> float:
        """
        One discrete update step = 1 second.
        """
        if is_on:
            alpha = alpha_on_1s
            T_target = T_max
        else:
            alpha = alpha_off_1s
            T_target = T_ambient

        return T_prev + alpha * (T_target - T_prev)

    # --------------------------------
    # FIT HEATING: estimate T_max + alpha_on_1s
    # --------------------------------
    def fit_heating(
        self,
        times_sec: list[float],
        temperatures: list[float],
        T_ambient: float
    ) -> tuple[float, float]:
        """
        Fit heating-only data (ON phase).
        Returns: (alpha_on_1s, T_max)
        Uses continuous-time exponential then converts to per-second alpha.
        """

        t = np.array(times_sec, dtype=float)
        y = np.array(temperatures, dtype=float)

        if len(y) < 3:
            raise ValueError("Need at least 3 heating points to fit.")

        t0 = t[0]
        T0 = y[0]

        # Heating model: T(t) = T_max + (T0 - T_max) * exp(-k*(t-t0))
        def heating_model(t, T_max, k):
            dt = t - t0
            return T_max + (T0 - T_max) * np.exp(-k * dt)

        T_max_guess = float(np.nanmax(y))
        k_guess = 1e-4

        (T_max_est, k_est), _ = curve_fit(
            heating_model,
            t,
            y,
            p0=[T_max_guess, k_guess],
            bounds=([T_ambient, 0], [2000, 2])
        )

        # Convert continuous k to per-second alpha
        alpha_on_1s = 1.0 - np.exp(-k_est)
        return float(alpha_on_1s), float(T_max_est)

    # --------------------------------
    # FIT COOLING: estimate alpha_off_1s
    # --------------------------------
    def fit_cooling(
        self,
        times_sec: list[float],
        temperatures: list[float],
        T_ambient: float
    ) -> float:
        """
        Fit cooling-only data (OFF phase).
        Returns: alpha_off_1s
        """

        t = np.array(times_sec, dtype=float)
        y = np.array(temperatures, dtype=float)

        if len(y) < 3:
            raise ValueError("Need at least 3 cooling points to fit.")

        t0 = t[0]
        T0 = y[0]

        # Cooling model: T(t) = T_ambient + (T0 - T_ambient) * exp(-k*(t-t0))
        def cooling_model(t, k):
            dt = t - t0
            return T_ambient + (T0 - T_ambient) * np.exp(-k * dt)

        k_guess = 1e-4

        (k_est,), _ = curve_fit(
            cooling_model,
            t,
            y,
            p0=[k_guess],
            bounds=([0], [2])
        )

        alpha_off_1s = 1.0 - np.exp(-k_est)
        return float(alpha_off_1s)
