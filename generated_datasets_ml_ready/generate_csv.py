
import os, math
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

# ---------- CONFIG ----------
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Noida"]
HOSPITALS_PER_CITY = 3
DAYS_BACK = 183  # approx 6 months

OUTPUT_BASE = "generated_datasets_ml_ready"
XGB_DIR = os.path.join(OUTPUT_BASE, "xgb")
TFT_DIR = os.path.join(OUTPUT_BASE, "tft")
os.makedirs(XGB_DIR, exist_ok=True)
os.makedirs(TFT_DIR, exist_ok=True)

# City parameters
CITY_PARAMS = {
    "Mumbai":    {"aqi_base": 120, "pop_density": 20400, "temp_mean": 28},
    "Delhi":     {"aqi_base": 260, "pop_density": 11200, "temp_mean": 30},
    "Bengaluru": {"aqi_base": 80,  "pop_density": 11200, "temp_mean": 24},
    "Hyderabad": {"aqi_base": 140, "pop_density": 10400, "temp_mean": 29},
    "Noida":     {"aqi_base": 220, "pop_density": 9000,  "temp_mean": 31},
}

# Festival / holiday offsets
FESTIVAL_OFFSETS = [30, 90]
HOLIDAY_OFFSETS = [15, 60]

# Random generator (fixed seed for reproducibility)
RNG = np.random.default_rng(42)

def seasonal_component(doy, amp=1.0, phase=0.0):
    return amp * math.sin(2 * math.pi * (doy / 365) + phase)

def small_jitter(ordinal, cidx, hidx, scale=1.0):
    x = ordinal * 0.13 + cidx * 0.7 + hidx * 0.37
    return math.sin(x) * scale

def deterministic_aqi(city, city_idx, date, FESTIVAL_DATES):
    base = CITY_PARAMS[city]["aqi_base"]
    doy = date.timetuple().tm_yday

    season_amp = 60 if city in ["Delhi", "Noida"] else (40 if city == "Hyderabad" else 30)
    season = season_amp * seasonal_component(doy)

    weekday_effect = 10 if date.weekday() < 5 else -5

    festival_spike = 0
    for fest in FESTIVAL_DATES:
        if abs((date - fest).days) <= 1:
            festival_spike += 80

    jitter = small_jitter(date.toordinal(), city_idx, 0, 3.0)

    return max(10, int(base + season + weekday_effect + festival_spike + jitter))

def deterministic_weather(city, city_idx, date):
    temp_mean = CITY_PARAMS[city]["temp_mean"]
    doy = date.timetuple().tm_yday

    amp = 8 if city == "Delhi" else 4
    temp = temp_mean + amp * seasonal_component(doy, phase=0.5)

    temp += small_jitter(date.toordinal(), city_idx, 1, 0.8)

    humidity = 60 + 15 * seasonal_component(doy, phase=-0.3)
    humidity = max(20, min(95, humidity))

    month = date.month
    if city == "Mumbai":
        rainfall = 40 if month in [6,7,8,9] else 2
    elif city in ["Bengaluru","Hyderabad"]:
        rainfall = 12 if month in [6,7,8,9] else 3
    else:
        rainfall = 6 if month in [7,8,9] else 1

    rainfall += abs(int(5 * seasonal_component(doy)))

    wind_speed = 3 + 1.5 * seasonal_component(doy)
    wind_speed = max(0.5, wind_speed)

    return round(temp,2), round(humidity,2), round(rainfall,2), round(wind_speed,2)

def deterministic_mobility(city, city_idx, date, FESTIVAL_DATES):
    base = 100 - CITY_PARAMS[city]["pop_density"]/1000

    if date.weekday() >= 5:
        base -= 10

    for fest in FESTIVAL_DATES:
        if abs((date - fest).days) <= 1:
            base -= 25

    return int(max(20, min(110, base)))

def outbreak_index(date):
    dn = date.toordinal()
    if dn % 111 == 0:
        return 1.0
    if dn % 37 == 0:
        return 0.4
    return 0.0

def hospital_attributes(city, idx):
    pop = CITY_PARAMS[city]["pop_density"]
    beds = int(50 + pop/500 + 20*idx)
    staff = int(20 + pop/2000 + 10*idx)
    base = int(80 + pop/200 + 10*idx)
    return beds, staff, base
def compute_admissions(base, aqi, temp, mobility, rainfall, fest, holi, outbreak,
                       weekday, city_idx, hosp_idx, date):
    """
    Compute admissions as a smooth baseline plus explainable spikes driven by
    correlated features (AQI, rainfall, outbreak, festivals, holidays, shocks).
    """
    doy = date.timetuple().tm_yday

    # ------------------------- Baseline & Seasonality -------------------------
    weekday_adj = 10 if weekday in [0, 1] else (-12 if weekday in [5, 6] else 0)

    # Smooth seasonal illness wave (higher in certain periods)
    seasonal_wave = 8 * seasonal_component(doy, amp=1.0, phase=0.2)

    # Temperature discomfort (cold/heat waves)
    beta_cold = 0.6 * max(0, 25 - temp)
    beta_heat = 0.4 * max(0, temp - 34)

    # Base trend by city/hospital
    drift = 0.02 * (city_idx + 1) * hosp_idx

    baseline = base + weekday_adj + seasonal_wave + beta_cold + beta_heat + drift

    # ------------------------ AQI-driven spikes -------------------------------
    aqi_excess = max(0, aqi - 150)
    if aqi_excess > 0:
        # High AQI days add between +30 and +80 admissions, scaled by severity
        aqi_spike = RNG.integers(30, 81) * (aqi_excess / 150)
    else:
        aqi_spike = 0.0

    # ------------------------ Rainfall-driven spikes --------------------------
    heavy_rain = max(0, rainfall - 30)
    if heavy_rain > 0:
        # Heavy rainfall days add between +20 and +50 admissions
        rain_spike = RNG.integers(20, 51) * (heavy_rain / 40)
    else:
        rain_spike = 0.0

    # ------------------------ Outbreak-driven spikes --------------------------
    if outbreak >= 1.0:
        # Major outbreak spike: +40 to +120
        outbreak_spike = RNG.integers(40, 121)
    elif outbreak >= 0.4:
        # Moderate outbreak
        outbreak_spike = RNG.integers(20, 61)
    else:
        outbreak_spike = 0.0

    # ------------------------ Festival / Holiday effects ----------------------
    festival_spike = RNG.integers(10, 41) if fest else 0.0
    holiday_mul = 0.88 if holi else 1.0

    # ------------------------ Mobility effect ---------------------------------
    mobility_effect = -0.025 * max(0, 100 - mobility)

    # ------------------------ Rare shock events (Poisson) ---------------------
    # Low-rate Poisson process, shocks still tied to outbreak/AQI severity.
    shock = 0.0
    if RNG.poisson(0.02) > 0:
        # Correlate shocks with existing stressors so they're explainable
        severity_factor = (aqi_excess / 150.0) + outbreak
        if severity_factor > 0:
            shock = RNG.integers(40, 121) * min(severity_factor, 2.0)

    # ------------------------ Aggregate all contributions --------------------
    explained_spikes = (
        aqi_spike
        + rain_spike
        + outbreak_spike
        + festival_spike
        + mobility_effect
        + shock
    )

    val = baseline + explained_spikes

    # Apply outbreak & holiday multipliers
    outbreak_mul = 1.0 + outbreak * 0.6
    val *= outbreak_mul * holiday_mul

    # ------------------------ Realistic noise ---------------------------------
    # Smooth Gaussian noise with city/hospital-specific correlation
    noise_seasonal = 2.5 * seasonal_component(doy, amp=1.0, phase=-0.1)
    noise_gauss = RNG.normal(0, 3.0)

    # Deterministic micro-variation
    micro = small_jitter(date.toordinal(), city_idx, hosp_idx, 1.2)

    val += noise_seasonal + noise_gauss + micro

    # Ensure non-negative and minimum admissions
    return max(5, int(round(val)))


# ---------- BUILD DATA ----------
TODAY = datetime.today().date()
start_date = TODAY - timedelta(days=DAYS_BACK-1)
dates = [start_date + timedelta(days=i) for i in range(DAYS_BACK)]

FESTIVAL_DATES = [start_date + timedelta(days=off) for off in FESTIVAL_OFFSETS]
HOLIDAYS = [start_date + timedelta(days=off) for off in HOLIDAY_OFFSETS]

for city_idx, city in enumerate(CITIES):
    all_rows_xgb = []
    all_rows_tft = []

    for hosp_idx in range(HOSPITALS_PER_CITY):
        hospital_id = f"{city[:3].upper()}H{hosp_idx+1}"
        beds, staff, base = hospital_attributes(city, hosp_idx)

        # Store series for lag/rolling
        aqi_s = []
        temp_s = []
        humid_s = []
        rain_s = []
        wind_s = []
        mob_s = []
        out_s = []
        adm_s = []

        for d in dates:
            aqi = deterministic_aqi(city, city_idx, d, FESTIVAL_DATES)
            temp, hum, rain, wind = deterministic_weather(city, city_idx, d)
            mobility = deterministic_mobility(city, city_idx, d, FESTIVAL_DATES)
            out = outbreak_index(d)
            weekday = d.weekday()
            fest = int(any(abs((d-f).days) <= 1 for f in FESTIVAL_DATES))
            holi = int(d in HOLIDAYS)

            admissions = compute_admissions(base, aqi, temp, mobility, rain, fest, holi, out, weekday, city_idx, hosp_idx, d)


            aqi_s.append(aqi)
            temp_s.append(temp)
            humid_s.append(hum)
            rain_s.append(rain)
            wind_s.append(wind)
            mob_s.append(mobility)
            out_s.append(out)
            adm_s.append(admissions)

        # Lags + rolling
        lag1 = [adm_s[i-1] if i-1>=0 else adm_s[0] for i in range(len(adm_s))]
        lag7 = [adm_s[i-7] if i-7>=0 else adm_s[0] for i in range(len(adm_s))]
        roll14=[]
        for i in range(len(adm_s)):
            s=max(0,i-13)
            roll14.append(round(sum(adm_s[s:i+1])/(i-s+1),2))

        # Write rows
        for i, d in enumerate(dates):
            weekday=d.weekday()
            fest=int(any(abs((d-f).days)<=1 for f in FESTIVAL_DATES))
            holi=int(d in HOLIDAYS)
            is_weekend=1 if weekday>=5 else 0

            row_xgb = {
                "date": d,
                "city": city,
                "city_id": city_idx,
                "hospital_id": hospital_id,
                "hospital_id_enc": hosp_idx,
                "admissions": adm_s[i],
                "lag_1_admissions": lag1[i],
                "lag_7_admissions": lag7[i],
                "rolling_14_admissions": roll14[i],
                "aqi": aqi_s[i],
                "temp": temp_s[i],
                "humidity": humid_s[i],
                "rainfall": rain_s[i],
                "wind_speed": wind_s[i],
                "mobility_index": mob_s[i],
                "outbreak_index": out_s[i],
                "festival_flag": fest,
                "holiday_flag": holi,
                "weekday": weekday,
                "is_weekend": is_weekend,
                "population_density": CITY_PARAMS[city]["pop_density"],
                "hospital_beds": beds,
                "staff_count": staff
            }
            all_rows_xgb.append(row_xgb)

            # TFT requires future-known covariates
            fut_aqi=[]; fut_temp=[]; fut_rain=[]
            for h in range(1,8):
                fd = d + timedelta(days=h)
                faqi = deterministic_aqi(city, city_idx, fd, FESTIVAL_DATES)
                ftemp, _, frain, _ = deterministic_weather(city, city_idx, fd)
                fut_aqi.append(faqi)
                fut_temp.append(ftemp)
                fut_rain.append(frain)

            tft_row = {
                "date": d,
                "time_idx": (d-start_date).days,
                "group_id": hospital_id,
                "city_id": city_idx,
                "hospital_id_enc": hosp_idx,
                "hospital_beds": beds,
                "staff_count": staff,
                "population_density": CITY_PARAMS[city]["pop_density"],
                "admissions": adm_s[i],
                "lag_1_admissions": lag1[i],
                "lag_7_admissions": lag7[i],
                "rolling_14_admissions": roll14[i],
                "aqi": aqi_s[i],
                "temp": temp_s[i],
                "humidity": humid_s[i],
                "rainfall": rain_s[i],
                "wind_speed": wind_s[i],
                "mobility_index": mob_s[i],
                "outbreak_index": out_s[i],
                "festival_flag": fest,
                "holiday_flag": holi,
                "weekday": weekday,
                "is_weekend": is_weekend,
            }

            for h in range(7):
                tft_row[f"aqi_forecast_{h+1}"] = fut_aqi[h]
                tft_row[f"temp_forecast_{h+1}"] = fut_temp[h]
                tft_row[f"rainfall_forecast_{h+1}"] = fut_rain[h]

            all_rows_tft.append(tft_row)

    df_xgb = pd.DataFrame(all_rows_xgb)
    df_tft = pd.DataFrame(all_rows_tft)

    df_xgb.to_csv(f"{XGB_DIR}/{city.lower()}_xgb.csv", index=False)
    df_tft.to_csv(f"{TFT_DIR}/{city.lower()}_tft.csv", index=False)

    print(f"Generated for: {city}")

print("Finished. All CSVs saved inside:", OUTPUT_BASE)
