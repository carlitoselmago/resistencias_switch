import csv
import requests
import logging
from logging.handlers import TimedRotatingFileHandler

from pathlib import Path
from time import perf_counter, sleep, time, localtime, strftime
from concurrent.futures import ThreadPoolExecutor
import argparse

from temp import temp
from helpers import helpers


# =============================
# CLI ARGUMENTS
# =============================

parser = argparse.ArgumentParser(description="Resistance temperature control service")
parser.add_argument(
    "--init-temps",
    nargs="*",
    type=float,
    help="Optional initial temperatures per resistance (up to 6 values)"
)
args = parser.parse_args()

INIT_TEMPS_OVERRIDE = args.init_temps or []


# =============================
# OUTPUT MODE
# =============================

USE_PRINT = True   # True = print(), False = logging


# =============================
# LOGGING SETUP
# =============================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name, logfile, level):
    handler = TimedRotatingFileHandler(
        logfile,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


log = setup_logger("service", LOG_DIR / "service.log", logging.INFO)
error_log = setup_logger("errors", LOG_DIR / "errors.log", logging.ERROR)


# =============================
# OUTPUT HELPERS
# =============================

def info(msg):
    if USE_PRINT:
        print(msg, flush=True)
    else:
        log.info(msg)

def warning(msg):
    if USE_PRINT:
        print(f"WARNING: {msg}", flush=True)
    else:
        log.warning(msg)

def error(msg):
    if USE_PRINT:
        print(f"ERROR: {msg}", flush=True)
    else:
        error_log.error(msg)


# =============================
# CONFIG
# =============================

csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?output=csv"
local_csv_path = Path("cached_google_sheet.csv")

step = 5          # minutes per step
room_temp = 18    # °C
max_temp = 100    # safety limit


# =============================
# INIT
# =============================

T = temp()
H = helpers()

IPS = []
HYPER = []
temps = []
seq = []

info("Service starting")


# =============================
# THREAD POOL FOR HTTP CALLS
# =============================

HTTP_POOL = ThreadPoolExecutor(max_workers=8)


# =============================
# TASMOTA CONTROLLERS
# =============================

def on(HOST):
    try:
        r = requests.get(
            f"http://{HOST}/cm?cmnd=Power On",
            timeout=5
        )
        r.raise_for_status()
        info(f"Power ON -> {HOST}")
        return True
    except requests.exceptions.RequestException as e:
        error(f"FAILED Power ON -> {HOST} ({e})")
        return False


def off(HOST):
    try:
        r = requests.get(
            f"http://{HOST}/cm?cmnd=Power Off",
            timeout=5
        )
        r.raise_for_status()
        info(f"Power OFF -> {HOST}")
        return True
    except requests.exceptions.RequestException as e:
        error(f"FAILED Power OFF -> {HOST} ({e})")
        return False


def on_async(HOST):
    HTTP_POOL.submit(on, HOST)


def off_async(HOST):
    HTTP_POOL.submit(off, HOST)


# =============================
# LOAD CSV
# =============================

info("Loading CSV configuration")
csv_data = H.google_csv_to_list(csv_url, local_csv_path)

seq_start = False

for r in csv_data:

    if r[0] == "IP":
        for ip in range(1, 6):
            if r[ip]:
                IPS.append(r[ip])

        info(f"Loaded IPs: {IPS}")

        # cleanup: ensure all off
        info("Ensuring all resistances are OFF")
        for ip in IPS:
            off_async(ip)

        # build initial temperature row
        initial_row = []
        for i in range(len(IPS)):
            if i < len(INIT_TEMPS_OVERRIDE):
                initial_row.append(INIT_TEMPS_OVERRIDE[i])
            else:
                initial_row.append(room_temp)

        temps.append(initial_row)

        info(f"Initial temperatures: {initial_row}")

    if r[0] == "alpha":
        for i in range(1, 6):
            if r[i]:
                HYPER.append({"alpha": float(r[i])})

    if r[0] == "alpha_off":
        for i in range(1, 6):
            if r[i]:
                HYPER[i - 1]["alpha_off"] = float(r[i])

    if r[0] == "t_max":
        for i in range(1, 6):
            if r[i]:
                HYPER[i - 1]["t_max"] = float(r[i])

    if r[0] == "Secuencia":
        seq_start = True

    if seq_start:
        for _ in range(step * 60):
            row = []
            for res in range(6):
                row.append(bool(r[res]))
            seq.append(row)

info(f"Sequence length: {len(seq)} seconds")


# =============================
# MAIN LOOP
# =============================

period_s = 1.0
next_tick = perf_counter() + period_s

for i, s in enumerate(seq):

    temprow = []

    for index, state in enumerate(s):

        if index < len(IPS):
            t_prev = temps[-1][index]
            alpha = HYPER[index]["alpha"]
            alpha_off = HYPER[index]["alpha_off"]
            t_max = HYPER[index]["t_max"]

            if state:
                t_now = T.update_temperature(
                    t_prev, True, room_temp, t_max, alpha, alpha_off
                )

                if t_now >= max_temp:
                    warning(
                        f"Cooling off resistance {index} (temp={t_now:.2f})"
                    )
                    off_async(IPS[index])
                    t_now = T.update_temperature(
                        t_prev, False, room_temp, t_max, alpha, alpha_off
                    )
                else:
                    on_async(IPS[index])

            else:
                t_now = T.update_temperature(
                    t_prev, False, room_temp, t_max, alpha, alpha_off
                )
                off_async(IPS[index])

            temprow.append(t_now)

    temps.append(temprow)

    if i % 60 == 0:
        info(
            f"minute={i // 60} "
            f"time={strftime('%Y-%m-%d %H:%M:%S', localtime(time()))} "
            f"state={s} temps={temprow}"
        )

    now = perf_counter()
    remaining = next_tick - now

    if remaining > 0:
        sleep(remaining)
        next_tick += period_s
    else:
        next_tick = now + period_s


# =============================
# CLEAN SHUTDOWN
# =============================

info("Waiting for pending HTTP commands")
HTTP_POOL.shutdown(wait=True)

info("Service finished cleanly")
