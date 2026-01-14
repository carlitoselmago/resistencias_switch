import numpy as np
from scipy.optimize import curve_fit


class temp:

    def __init__(self):
        pass

    def update_temperature(
        self,
        T_prev: float,
        is_on: bool,
        T_ambient: float,
        T_max: float,
        alpha: float
    ) -> float:

        T_target = T_max if is_on else T_ambient
        return T_prev + alpha * (T_target - T_prev)

    # -------------------------------
    # PARAMETER ESTIMATION
    # -------------------------------

    def estimate_alpha_and_Tmax(
        self,
        temperatures: list[float],
        T_ambient: float,
        sample_interval_sec: int = 300
    ) -> tuple[float, float]:
        """
        Estimate alpha and T_max from temperature readings.

        Parameters
        ----------
        temperatures : list of float
            Temperature readings in Celsius (every 5 minutes by default)
        T_ambient : float
            Ambient temperature (heater fully off)
        sample_interval_sec : int
            Time between samples in seconds (default: 300s = 5 min)

        Returns
        -------
        alpha : float
            Discrete-time thermal coefficient (per second)
        T_max : float
            Estimated steady-state temperature when ON
        """

        temps = np.array(temperatures)
        t = np.arange(len(temps)) * sample_interval_sec
        T0 = temps[0]

        # Model for heating phase
        def model(t, T_max, k):
            return T_max + (T0 - T_max) * np.exp(-k * t)

        # Initial guesses (important but intuitive)
        T_max_guess = max(temps)
        k_guess = 1e-4

        params, _ = curve_fit(
            model,
            t,
            temps,
            p0=[T_max_guess, k_guess],
            bounds=([T_ambient, 0], [2000, 1])
        )

        T_max_est, k_est = params

        # Convert continuous k to discrete alpha (1-second step)
        alpha_est = 1 - np.exp(-k_est)

        return alpha_est, T_max_est
