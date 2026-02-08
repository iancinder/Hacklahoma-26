import os
import joblib
import pandas as pd


def fmt_pace(sec_per_mi: int) -> str:
    m = sec_per_mi // 60
    s = sec_per_mi % 60
    return f"{m}:{s:02d}"


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "model_time.pkl")
    model = joblib.load(model_path)

    # A few representative scenarios to sanity-check time/pace.
    # Tune these as needed for your demo trails.
    scenarios = [
        # Typical hike
        dict(weight_lb=160, age=22, fitness_level=0.5, distance_mi=5.0, elevation_gain_ft=800,
             flat_speed_mph=3.0, vertical_speed_fph=1000, difficulty="moderate", activity_type="hiking"),
        # Easy flat hike
        dict(weight_lb=160, age=22, fitness_level=0.5, distance_mi=3.0, elevation_gain_ft=100,
             flat_speed_mph=3.0, vertical_speed_fph=1000, difficulty="easy", activity_type="hiking"),
        # Steep hike
        dict(weight_lb=160, age=22, fitness_level=0.5, distance_mi=4.0, elevation_gain_ft=2000,
             flat_speed_mph=3.0, vertical_speed_fph=900, difficulty="hard", activity_type="hiking"),
        # Trail run
        dict(weight_lb=160, age=22, fitness_level=0.7, distance_mi=5.0, elevation_gain_ft=500,
             flat_speed_mph=7.0, vertical_speed_fph=1400, difficulty="moderate", activity_type="running"),
    ]

    df = pd.DataFrame(scenarios)
    pred_time_hr = model.predict(df)

    print(f"Loaded model: {model_path}")
    for row, t_hr in zip(scenarios, pred_time_hr):
        dist = row["distance_mi"]
        sec_per_mi = int(round((t_hr * 3600) / dist)) if dist > 0 else 0
        print(
            f"- {row['activity_type']}/{row['difficulty']}  "
            f"{dist}mi  gain={row['elevation_gain_ft']}ft  "
            f"time={t_hr:.2f}hr  pace={fmt_pace(sec_per_mi)} min/mi ({sec_per_mi} sec/mi)"
        )


if __name__ == "__main__":
    main()

