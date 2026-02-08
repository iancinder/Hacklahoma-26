'''
Trail Profile via OpenRouteService

Fetches a hiking route with elevation data between two GPS coordinates,
analyzes the elevation profile, and generates an Elevation vs Time graph.
'''

import requests
import math
import io
import base64

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (no GUI window)
import matplotlib.pyplot as plt
import numpy as np

# ---- OpenRouteService API Key ----
_ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjVlMmE0ZGI5ODE5YTQ2OTE5ZjFjNDI0Yzg1OWRmMzQwIiwiaCI6Im11cm11cjY0In0="

def set_api_key(key):
    global _ORS_API_KEY
    _ORS_API_KEY = key


# ---------- API Call ----------

def fetch_route(start_lon, start_lat, end_lon, end_lat):
    """
    Fetch a hiking route with elevation from OpenRouteService.
    Returns list of [lon, lat, elevation_meters] coordinates along the trail.
    """
    if not _ORS_API_KEY:
        raise ValueError("OpenRouteService API key not set. Set ORS_API_KEY in your environment.")

    url = "https://api.openrouteservice.org/v2/directions/foot-hiking/geojson"
    headers = {
        "Authorization": _ORS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
        "elevation": True
    }

    resp = requests.post(url, json=body, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    # GeoJSON: features[0].geometry.coordinates = [[lon, lat, elev_m], ...]
    coords = data["features"][0]["geometry"]["coordinates"]
    return coords


# ---------- Profile Analysis ----------

def _haversine_m(lat1, lon1, lat2, lon2):
    """Haversine distance in meters between two lat/lon points (degrees)."""
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def analyze_profile(coords):
    """
    Analyze the elevation profile from ORS coordinates.

    coords:  list of [lon, lat, elevation_m]
    Returns: dict with distance_mi, elevation_gain_ft, elevation_loss_ft, segments
             segments = [(cumulative_miles, elevation_ft), ...]
    """
    total_dist_m = 0.0
    total_gain_m = 0.0
    total_loss_m = 0.0

    M_TO_FT = 3.28084
    M_TO_MI = 1 / 1609.344

    segments = [(0.0, coords[0][2] * M_TO_FT)]

    for i in range(1, len(coords)):
        lon1, lat1, elev1 = coords[i - 1]
        lon2, lat2, elev2 = coords[i]

        d = _haversine_m(lat1, lon1, lat2, lon2)
        total_dist_m += d

        d_elev = elev2 - elev1
        if d_elev > 0:
            total_gain_m += d_elev
        else:
            total_loss_m += abs(d_elev)

        segments.append((total_dist_m * M_TO_MI, elev2 * M_TO_FT))

    return {
        "distance_mi":      round(total_dist_m * M_TO_MI, 2),
        "elevation_gain_ft": round(total_gain_m * M_TO_FT, 0),
        "elevation_loss_ft": round(total_loss_m * M_TO_FT, 0),
        "segments":          segments,   # [(cumulative_miles, elevation_ft), ...]
    }


# ---------- Pace-Adjusted Time ----------

def compute_elevation_vs_time(segments, base_pace_min_per_mi):
    """
    Walk through each segment, adjust pace for the local grade, and
    accumulate elapsed time.

    segments:              [(cumulative_miles, elevation_ft), ...]
    base_pace_min_per_mi:  overall predicted pace (min / mile)

    Returns: [(cumulative_time_min, elevation_ft), ...]
    """
    result = [(0.0, segments[0][1])]
    cumulative_time = 0.0

    for i in range(1, len(segments)):
        dist_prev, elev_prev = segments[i - 1]
        dist_curr, elev_curr = segments[i]

        seg_dist_mi = dist_curr - dist_prev
        if seg_dist_mi <= 0:
            result.append((cumulative_time, elev_curr))
            continue

        # Grade in percent
        seg_dist_ft = seg_dist_mi * 5280
        d_elev_ft   = elev_curr - elev_prev
        grade_pct   = (d_elev_ft / seg_dist_ft) * 100 if seg_dist_ft > 0 else 0

        # Grade → pace multiplier
        if grade_pct > 0:                       # Uphill
            grade_factor = 1.0 + grade_pct * 0.06
        elif grade_pct > -10:                   # Mild downhill (speed boost)
            grade_factor = 1.0 + grade_pct * 0.03
        else:                                   # Steep downhill (harder)
            grade_factor = 1.0 - 10 * 0.03 + (grade_pct + 10) * 0.02

        grade_factor = max(0.5, min(grade_factor, 3.0))   # clamp

        adjusted_pace = base_pace_min_per_mi * grade_factor
        cumulative_time += adjusted_pace * seg_dist_mi

        result.append((cumulative_time, elev_curr))

    return result


# ---------- Graph Generation ----------

def generate_elevation_time_graph(time_elev_data):
    """
    Create an Elevation-vs-Time graph and return it as a base64 PNG string.

    time_elev_data: [(cumulative_time_min, elevation_ft), ...]
    """
    times      = [t for t, _ in time_elev_data]
    elevations = [e for _, e in time_elev_data]

    # Choose hours or minutes for x-axis
    max_time = max(times) if times else 0
    if max_time > 120:
        times_display = [t / 60 for t in times]
        time_label = "Time (hours)"
    else:
        times_display = times
        time_label = "Time (minutes)"

    # Normalize elevations so the y-axis naturally spans only the
    # elevation *change*, then relabel ticks with real values.
    # This avoids any set_ylim issues with matplotlib.
    elev_min = min(elevations)
    elevations_shifted = [e - elev_min for e in elevations]

    fig = plt.figure(figsize=(4.8, 2.6), dpi=130)
    ax = fig.add_subplot(111)

    # Colour-code uphill (red) vs downhill (green) segments
    for i in range(1, len(times_display)):
        color = '#e74c3c' if elevations_shifted[i] >= elevations_shifted[i - 1] else '#27ae60'
        ax.fill_between(
            times_display[i - 1:i + 1],
            [0, 0],
            elevations_shifted[i - 1:i + 1],
            alpha=0.30, color=color
        )

    # Main elevation line
    ax.plot(times_display, elevations_shifted, color='#2c3e50', linewidth=1.5)

    # Relabel y-ticks to show actual elevation (add elev_min back)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda y, _: f'{int(y + elev_min)}')
    )

    ax.set_xlabel(time_label, fontsize=9, color='#555')
    ax.set_ylabel("Elevation (ft)", fontsize=9, color='#555')
    ax.set_title("Elevation vs Estimated Time", fontsize=11,
                 fontweight='bold', color='#333')
    ax.tick_params(labelsize=8, colors='#666')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor='white')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')
