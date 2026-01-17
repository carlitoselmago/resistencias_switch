from temp import temp
from helpers import helpers
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# =============================
# LOAD DATA
# =============================

H = helpers()

csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?gid=1438086701&single=true&output=csv"
local_csv_path = Path("cached_google_sheet_medidas.csv")

csv_data = H.google_csv_to_list(csv_url, local_csv_path)

# 6 resistances, fixed 5-minute grid
readings = [[] for _ in range(6)]


# =============================
# PARSE CSV (FIRST 7 COLUMNS, KEEP GAPS)
# =============================

for row_i, row in enumerate(csv_data):
    if row_i == 0:
        continue  # header

    # col 0 = time label, col 1..6 = resistances
    for col_i in range(1, 7):
        if col_i < len(row) and row[col_i] != "":
            readings[col_i - 1].append(float(row[col_i]))
        else:
            readings[col_i - 1].append(np.nan)


# =============================
# SETTINGS
# =============================

model = temp()

T_AMBIENT = 21.5
STEP_SEC = 300  # 5 minutes per row


# =============================
# PROCESS + PLOT
# =============================

for ridx, series in enumerate(readings):

    series = np.array(series, dtype=float)

    if np.all(np.isnan(series)):
        continue

    print("\n" + ":" * 80)
    print(f"PROCESSING RESISTANCE {ridx}")
    print(":" * 80)

    # Full 5-min grid time (seconds)
    grid_times_sec = np.arange(len(series)) * STEP_SEC

    # Valid samples (keep real timestamps!)
    valid_idx = np.where(~np.isnan(series))[0]
    temps_valid = series[valid_idx]
    times_valid = grid_times_sec[valid_idx]

    if len(temps_valid) < 3:
        print("Not enough data to fit. Skipping.")
        continue

    # -----------------------------
    # FIND PEAK (FIRST GUESS)
    # -----------------------------

    peak_valid_pos = int(np.argmax(temps_valid))
    peak_grid_idx = int(valid_idx[peak_valid_pos])

    # -----------------------------
    # HELPER: TRY FIT WITH A GIVEN SPLIT
    # -----------------------------

    def try_fit(split_grid_idx: int):
        heat_mask = valid_idx <= split_grid_idx
        cool_mask = valid_idx >= split_grid_idx

        heat_times = times_valid[heat_mask]
        heat_temps = temps_valid[heat_mask]

        cool_times = times_valid[cool_mask]
        cool_temps = temps_valid[cool_mask]

        if len(heat_temps) < 3:
            return None

        alpha_on_1s, T_max = model.fit_heating(
            times_sec=heat_times.tolist(),
            temperatures=heat_temps.tolist(),
            T_ambient=T_AMBIENT
        )

        if len(cool_temps) >= 3:
            alpha_off_1s = model.fit_cooling(
                times_sec=cool_times.tolist(),
                temperatures=cool_temps.tolist(),
                T_ambient=T_AMBIENT
            )
        else:
            alpha_off_1s = None

        return alpha_on_1s, T_max, alpha_off_1s

    # -----------------------------
    # TRY FIT AT PEAK
    # -----------------------------

    fit = try_fit(peak_grid_idx)

    # -----------------------------
    # IF COOLING TOO SHORT → FIND FIRST DECREASE
    # -----------------------------

    if fit is None or fit[2] is None:
        split_candidate = None
        for j in range(peak_valid_pos + 1, len(temps_valid)):
            if temps_valid[j] < temps_valid[j - 1]:
                split_candidate = int(valid_idx[j])
                break

        if split_candidate is not None:
            fit = try_fit(split_candidate)
            if fit is not None:
                peak_grid_idx = split_candidate

    # -----------------------------
    # FINAL FALLBACK
    # -----------------------------

    if fit is None:
        print("ERROR: Unable to fit heating data. Skipping.")
        continue

    alpha_on_1s, T_max, alpha_off_1s = fit

    if alpha_off_1s is None:
        print("WARNING: Not enough cooling data.")
        print("         Using alpha_off = alpha_on as fallback.")
        alpha_off_1s = alpha_on_1s

    print(f"alpha_on_1s : {alpha_on_1s:.6f}")
    print(f"alpha_off_1s: {alpha_off_1s:.6f}")
    print(f"T_max       : {T_max:.2f}")
    print(f"OFF switch at grid idx {peak_grid_idx} (~{peak_grid_idx * 5} min)")

    # -----------------------------
    # SIMULATE USING PER-SECOND MODEL
    # -----------------------------

    temps_model = np.full_like(series, np.nan, dtype=float)

    first_grid_idx = int(valid_idx[0])
    temps_model[first_grid_idx] = series[first_grid_idx]

    for gi in range(first_grid_idx + 1, len(series)):

        # get previous modeled temperature
        prev = temps_model[gi - 1]
        if np.isnan(prev):
            back = gi - 1
            while back >= 0 and np.isnan(temps_model[back]):
                back -= 1
            if back < 0:
                break
            prev = temps_model[back]

        is_on = gi <= peak_grid_idx

        T = prev
        for _ in range(STEP_SEC):  # 300 per-second updates
            T = model.update_temperature(
                T_prev=T,
                is_on=is_on,
                T_ambient=T_AMBIENT,
                T_max=T_max,
                alpha_on_1s=alpha_on_1s,
                alpha_off_1s=alpha_off_1s
            )

        temps_model[gi] = T

    # -----------------------------
    # PLOT
    # -----------------------------

    plt.figure(figsize=(9, 4.5))

    plt.plot(
        grid_times_sec / 60,
        series,
        "o",
        label="Medidas termometro",
        alpha=0.7
    )

    plt.plot(
        grid_times_sec / 60,
        temps_model,
        "-",
        label="Modelo",
        linewidth=2
    )

    plt.axvline(
        (peak_grid_idx * STEP_SEC) / 60,
        linestyle="--",
        alpha=0.5,
        label="Apagado"
    )

    plt.xlabel("Tiempo en minutos")
    plt.ylabel("Temperatura")
    plt.title(f"Resistencia {ridx}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
