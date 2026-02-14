"""
DETERMINISTIC STRUCTURED HOSPITAL ADMISSIONS GENERATOR
------------------------------------------------------

Design Goals:
1. ZERO randomness (fully reproducible)
2. Clear additive structure
3. Delayed exogenous effects
4. Non-dominant static features
5. Strong forecasting signal
"""

import numpy as np
import pandas as pd
from datetime import datetime

# =====================================
# CONFIG
# =====================================

NUM_HOSPITALS = 10
START_DATE = "2018-01-01"
END_DATE = "2022-12-31"
BASE_RATE = 0.00035   # reduced so population doesn't dominate

# =====================================
# HELPERS
# =====================================

def get_season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10]:
        return "monsoon"
    else:
        return "spring"


def weekly_pattern(day):
    # deterministic weekly cycle
    pattern = [1.08, 1.04, 1.00, 1.00, 1.05, 0.92, 0.88]
    return pattern[day]


def yearly_seasonality(day_of_year):
    # smooth yearly wave
    return 1 + 0.12 * np.sin(2 * np.pi * day_of_year / 365)


def deterministic_outbreak(total_days):
    outbreak = np.zeros(total_days)

    for i in range(total_days):
        # periodic epidemic waves every ~300 days
        outbreak[i] = 50 * np.sin(2 * np.pi * i / 320) + 50

    return np.clip(outbreak, 0, 100)


def deterministic_aqi(total_days):
    aqi = np.zeros(total_days)

    for i in range(total_days):
        aqi[i] = 120 + 40 * np.sin(2 * np.pi * i / 365)

    return np.clip(aqi, 60, 250)


def deterministic_temperature(dates):
    temps = []
    for d in dates:
        day_of_year = d.timetuple().tm_yday
        temp = 30 - 10 * np.cos(2 * np.pi * day_of_year / 365)
        temps.append(temp)
    return np.array(temps)


# =====================================
# MAIN GENERATOR
# =====================================

def generate_dataset():

    dates = pd.date_range(start=START_DATE, end=END_DATE)
    total_days = len(dates)

    outbreak = deterministic_outbreak(total_days)
    aqi = deterministic_aqi(total_days)
    temperature = deterministic_temperature(dates)

    rows = []

    for h in range(NUM_HOSPITALS):

        # structured hospital metadata (no randomness)
        population = 300000 + h * 50000
        elderly_ratio = 0.08 + h * 0.01
        capacity = 300 + h * 40
        icu_capacity = int(capacity * 0.18)

        baseline = np.zeros(total_days)
        shock = np.zeros(total_days)
        interaction = np.zeros(total_days)

        # ------------------------------------
        # BASELINE
        # ------------------------------------
        for i, date in enumerate(dates):
            base = population * BASE_RATE
            base *= weekly_pattern(date.weekday())
            base *= yearly_seasonality(date.timetuple().tm_yday)
            baseline[i] = base

        # ------------------------------------
        # DELAYED SHOCK ENGINE
        # ------------------------------------
        for i in range(total_days):

            # AQI delayed respiratory load
            if aqi[i] > 160:
                if i + 3 < total_days:
                    shock[i + 3] += baseline[i] * 0.18

            # Outbreak delayed surge
            if outbreak[i] > 70:
                if i + 4 < total_days:
                    shock[i + 4] += baseline[i] * 0.30

        # ------------------------------------
        # INTERACTION ENGINE
        # ------------------------------------
        for i, date in enumerate(dates):

            # temperature stress × elderly
            if temperature[i] > 37 or temperature[i] < 8:
                interaction[i] += baseline[i] * elderly_ratio * 0.25

            # winter AQI amplification
            if date.month in [12, 1, 2] and aqi[i] > 170:
                interaction[i] += baseline[i] * 0.15

        # ------------------------------------
        # FINAL ASSEMBLY
        # ------------------------------------
        admissions = baseline + shock + interaction

        admissions = np.clip(admissions, 0, capacity * 1.15)
        admissions = admissions.astype(int)

        for i, date in enumerate(dates):
            rows.append({
                "date": date,
                "day_of_week": date.weekday(),
                "month": date.month,
                "week_of_year": date.isocalendar().week,
                "is_weekend": 1 if date.weekday() >= 5 else 0,
                "season": get_season(date.month),
                "temperature": round(temperature[i], 2),
                "aqi": round(aqi[i], 2),
                "outbreak_index": round(outbreak[i], 2),
                "mobility_index": 70 + 10 * np.sin(2 * np.pi * i / 14),
                "population": population,
                "population_density": 4000 + h * 300,
                "elderly_ratio": round(elderly_ratio, 3),
                "hospital_id": f"HOSP_{h+1}",
                "hospital_capacity": capacity,
                "icu_capacity": icu_capacity,
                "admissions": admissions[i]
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("synthetic_hospital_data.csv", index=False)
    print("Dataset generated:", df.shape)
