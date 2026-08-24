"""
Risk Engine — deterministic, rule-based weather risk scoring.

Formula
-------
Risk Score = (rainfall_severity  * 0.30)
           + (wind_severity       * 0.20)
           + (temperature_severity * 0.15)
           + (official_warning_severity * 0.35)

Each sub-score is a float in [0.0, 1.0] derived from clear, documented
thresholds.  No ML.  No probability.  Every number is traceable back to
a specific meteorological value and threshold.

Score → Level mapping
---------------------
  0.00 – 0.24   Low
  0.25 – 0.49   Moderate
  0.50 – 0.74   High
  0.75 – 1.00   Critical

This module is intentionally self-contained and pure (no I/O, no async).
Feed it a WeatherResponse object and get back a RiskResult.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.schemas.risk import AdvisoryResult, RiskLevel, RiskResult, SubScore
from app.schemas.weather import WeatherResponse


# ---------------------------------------------------------------------------
# Weights  (must sum to 1.0)
# ---------------------------------------------------------------------------

W_RAIN     = 0.30
W_WIND     = 0.20
W_TEMP     = 0.15
W_OFFICIAL = 0.35


# ---------------------------------------------------------------------------
# Threshold tables  (documented inline for full transparency)
# ---------------------------------------------------------------------------

# Rainfall severity — based on IMD (India Meteorological Dept) categories
# combined with next-6-hour accumulated precipitation from hourly data
#
#   0.0  →  0.00 mm      (dry)
#   0.2  →  < 2.5 mm     (light)
#   0.4  →  2.5–7.4 mm   (moderate)
#   0.6  →  7.5–35.4 mm  (heavy)
#   0.8  →  35.5–64.4 mm (very heavy)
#   1.0  →  ≥ 64.5 mm    (extremely heavy / cloud-burst level)

def _rainfall_severity(weather: WeatherResponse) -> Tuple[float, float, str]:
    """
    Returns (severity 0-1, raw_mm, threshold_note).
    Uses: max hourly precipitation probability in next 6 hours +
          next-6h accumulated precipitation from hourly data.
    """
    hourly = weather.hourly

    # Next 6 hours of precipitation (mm) and probability (%)
    precip_6h = sum(hourly.precipitation[:6])
    prob_6h_values = [p for p in hourly.precipitation_probability[:6] if p is not None]
    max_prob_6h = max(prob_6h_values) if prob_6h_values else 0

    # Also look at today's daily total for a broader signal
    daily_total = weather.daily.precipitation_sum[0] if weather.daily.precipitation_sum else 0.0

    # Use the larger of 6h accumulated or daily * fraction that's already fallen
    effective_mm = max(precip_6h, daily_total * 0.25)

    if effective_mm == 0 and max_prob_6h < 20:
        return 0.0, effective_mm, "Dry (< 0.1 mm expected, low probability)"
    elif effective_mm < 2.5 or max_prob_6h < 40:
        return 0.2, effective_mm, "Light rain possible (< 2.5 mm / low probability)"
    elif effective_mm < 7.5:
        return 0.4, effective_mm, "Moderate rain (2.5–7.4 mm)"
    elif effective_mm < 35.5:
        return 0.6, effective_mm, "Heavy rain (7.5–35.4 mm)"
    elif effective_mm < 64.5:
        return 0.8, effective_mm, "Very heavy rain (35.5–64.4 mm)"
    else:
        return 1.0, effective_mm, "Extremely heavy rain / cloudburst (≥ 64.5 mm)"


# Wind severity — based on Beaufort scale generalisation
#
#   0.0  →  < 20 km/h     (calm to light breeze)
#   0.2  →  20–38 km/h    (gentle to moderate breeze)
#   0.4  →  39–61 km/h    (fresh to strong breeze)
#   0.6  →  62–88 km/h    (near-gale to gale)
#   0.8  →  89–117 km/h   (strong gale to storm)
#   1.0  →  ≥ 118 km/h    (violent storm / hurricane force)

def _wind_severity(weather: WeatherResponse) -> Tuple[float, float, str]:
    """
    Returns (severity 0-1, raw_kmh, threshold_note).
    Uses max of current wind speed and today's max daily gusts.
    """
    current_speed = weather.current.wind_speed_10m
    daily_max_gust = (
        weather.daily.wind_gusts_10m_max[0]
        if weather.daily.wind_gusts_10m_max
        else 0.0
    )
    effective_kmh = max(current_speed, daily_max_gust)

    if effective_kmh < 20:
        return 0.0, effective_kmh, "Calm / light breeze (< 20 km/h)"
    elif effective_kmh < 39:
        return 0.2, effective_kmh, "Gentle to moderate breeze (20–38 km/h)"
    elif effective_kmh < 62:
        return 0.4, effective_kmh, "Fresh to strong breeze (39–61 km/h)"
    elif effective_kmh < 89:
        return 0.6, effective_kmh, "Near-gale to gale (62–88 km/h)"
    elif effective_kmh < 118:
        return 0.8, effective_kmh, "Strong gale to storm (89–117 km/h)"
    else:
        return 1.0, effective_kmh, "Violent storm / hurricane force (≥ 118 km/h)"


# Temperature severity — dual-sided: heat AND cold stress both score high
#
# Heat thresholds (feels-like apparent temperature):
#   0.0  →  < 35°C        (comfortable)
#   0.2  →  35–39°C       (caution: heat fatigue possible)
#   0.4  →  40–44°C       (danger: heat cramps / exhaustion)
#   0.7  →  45–49°C       (extreme danger: heat stroke likely)
#   1.0  →  ≥ 50°C        (catastrophic)
#
# Cold thresholds (feels-like):
#   0.2  →  0–9°C         (cold, dress warmly)
#   0.5  →  -10–-1°C      (very cold, frostbite risk)
#   0.8  →  ≤ -11°C       (dangerous cold)

def _temperature_severity(weather: WeatherResponse) -> Tuple[float, float, str]:
    """
    Returns (severity 0-1, raw_°C, threshold_note).
    Uses today's max apparent (feels-like) temperature.
    """
    feels_max = (
        weather.daily.apparent_temperature_max[0]
        if weather.daily.apparent_temperature_max
        else weather.current.apparent_temperature
    )
    feels_min = (
        weather.daily.apparent_temperature_min[0]
        if weather.daily.apparent_temperature_min
        else weather.current.apparent_temperature
    )

    # Heat stress dominates if feels_max is dangerous
    if feels_max >= 50:
        return 1.0, feels_max, "Catastrophic heat: feels like ≥ 50°C"
    elif feels_max >= 45:
        return 0.7, feels_max, "Extreme heat danger: feels like 45–49°C (heat stroke likely)"
    elif feels_max >= 40:
        return 0.4, feels_max, "Heat danger: feels like 40–44°C (heat exhaustion risk)"
    elif feels_max >= 35:
        return 0.2, feels_max, "Heat caution: feels like 35–39°C"
    # Cold stress
    elif feels_min <= -11:
        return 0.8, feels_min, "Dangerous cold: feels like ≤ -11°C (frostbite risk)"
    elif feels_min <= -1:
        return 0.5, feels_min, "Very cold: feels like -10 to -1°C"
    elif feels_min <= 9:
        return 0.2, feels_min, "Cold: feels like 0–9°C"
    else:
        return 0.0, feels_max, "Temperature within safe range"


# Official warning severity
# Placeholder for future alert integration (Section 7).
# alert_data is a dict with optional key "max_level" in {"minor","moderate","severe","extreme"}

_ALERT_LEVEL_MAP = {
    None: (0.0, "No active official warnings"),
    "minor": (0.25, "Minor official warning active"),
    "moderate": (0.5, "Moderate official warning active"),
    "severe": (0.75, "Severe official warning active"),
    "extreme": (1.0, "Extreme official warning active — all activities affected"),
}

def _official_warning_severity(
    alert_data: Optional[dict],
) -> Tuple[float, str, str]:
    """
    Returns (severity 0-1, raw_level_str, threshold_note).
    alert_data may be None (no alerts) or a dict with 'max_level'.
    """
    if not alert_data:
        sev, note = _ALERT_LEVEL_MAP[None]
        return sev, "none", note

    level = alert_data.get("max_level")  # "minor" | "moderate" | "severe" | "extreme"
    sev, note = _ALERT_LEVEL_MAP.get(level, (0.0, "Unknown alert level"))
    return sev, str(level), note


# ---------------------------------------------------------------------------
# Score → Level mapping
# ---------------------------------------------------------------------------

def _score_to_level(score: float) -> RiskLevel:
    if score < 0.25:
        return RiskLevel.LOW
    elif score < 0.50:
        return RiskLevel.MODERATE
    elif score < 0.75:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def calculate_risk(
    weather: WeatherResponse,
    alert_data: Optional[dict] = None,
    advisory: Optional[AdvisoryResult] = None,
) -> RiskResult:
    """
    Compute a deterministic composite risk score for the given weather data.

    Parameters
    ----------
    weather     : WeatherResponse from weather_service.get_forecast()
    alert_data  : Optional dict with 'max_level' key (wired in Section 7).
                  Pass None if no alert data is available yet.
    advisory    : Pre-computed AdvisoryResult (passed in from advisory_engine).
                  If None, an empty AdvisoryResult is used.

    Returns
    -------
    RiskResult with score, level, human-readable reasons, and sub-score breakdown.
    """
    # --- Compute each component -----------------------------------------
    rain_sev,   rain_raw,   rain_note   = _rainfall_severity(weather)
    wind_sev,   wind_raw,   wind_note   = _wind_severity(weather)
    temp_sev,   temp_raw,   temp_note   = _temperature_severity(weather)
    alert_sev,  alert_raw,  alert_note  = _official_warning_severity(alert_data)

    # --- Weighted composite ---------------------------------------------
    score = (
        rain_sev   * W_RAIN
      + wind_sev   * W_WIND
      + temp_sev   * W_TEMP
      + alert_sev  * W_OFFICIAL
    )
    score = round(min(max(score, 0.0), 1.0), 4)
    level = _score_to_level(score)

    # --- Sub-score breakdown --------------------------------------------
    sub_scores: List[SubScore] = [
        SubScore(
            name="rainfall_severity",
            raw_value=round(rain_raw, 2),
            unit="mm (6h accumulated)",
            severity=rain_sev,
            weight=W_RAIN,
            weighted=round(rain_sev * W_RAIN, 4),
            threshold_note=rain_note,
        ),
        SubScore(
            name="wind_severity",
            raw_value=round(wind_raw, 1),
            unit="km/h (max speed/gust)",
            severity=wind_sev,
            weight=W_WIND,
            weighted=round(wind_sev * W_WIND, 4),
            threshold_note=wind_note,
        ),
        SubScore(
            name="temperature_severity",
            raw_value=round(temp_raw, 1),
            unit="°C (feels-like)",
            severity=temp_sev,
            weight=W_TEMP,
            weighted=round(temp_sev * W_TEMP, 4),
            threshold_note=temp_note,
        ),
        SubScore(
            name="official_warning_severity",
            raw_value=0.0,
            unit="alert level",
            severity=alert_sev,
            weight=W_OFFICIAL,
            weighted=round(alert_sev * W_OFFICIAL, 4),
            threshold_note=alert_note,
        ),
    ]

    # --- Human-readable reasons  (only include non-trivial drivers) -----
    reasons: List[str] = []

    if rain_sev >= 0.6:
        reasons.append(f"⛈  Heavy rain expected ({rain_raw:.1f} mm) — {rain_note}")
    elif rain_sev >= 0.4:
        reasons.append(f"🌧  Moderate rain expected ({rain_raw:.1f} mm) — {rain_note}")
    elif rain_sev >= 0.2:
        reasons.append(f"🌦  Light rain possible ({rain_raw:.1f} mm) — {rain_note}")

    if wind_sev >= 0.6:
        reasons.append(f"💨  Dangerous winds ({wind_raw:.0f} km/h) — {wind_note}")
    elif wind_sev >= 0.4:
        reasons.append(f"💨  Strong winds ({wind_raw:.0f} km/h) — {wind_note}")
    elif wind_sev >= 0.2:
        reasons.append(f"💨  Moderate winds ({wind_raw:.0f} km/h) — {wind_note}")

    if temp_sev >= 0.7:
        reasons.append(f"🌡  Extreme heat ({temp_raw:.1f}°C feels-like) — {temp_note}")
    elif temp_sev >= 0.4:
        reasons.append(f"🌡  Dangerous heat ({temp_raw:.1f}°C feels-like) — {temp_note}")
    elif temp_sev >= 0.2:
        reasons.append(f"🌡  Heat / cold caution ({temp_raw:.1f}°C feels-like) — {temp_note}")

    if alert_sev >= 0.75:
        reasons.append(f"🚨  Official SEVERE/EXTREME warning active — {alert_note}")
    elif alert_sev >= 0.5:
        reasons.append(f"⚠️   Official MODERATE warning active — {alert_note}")
    elif alert_sev >= 0.25:
        reasons.append(f"ℹ️   Official MINOR warning active — {alert_note}")

    if not reasons:
        reasons.append("✅  No significant weather hazards detected at this time.")

    return RiskResult(
        score=score,
        level=level,
        reasons=reasons,
        sub_scores=sub_scores,
        advisory=advisory or AdvisoryResult(items=[], summary=None),
    )
