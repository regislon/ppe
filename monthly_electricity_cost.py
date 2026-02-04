import calendar

import pandas as pd

CONSUMERS = ["kwh_building", "kwh_0", "kwh_1", "kwh_2", "kwh_fridge"]


def _days_in_month(month_year: str) -> int:
    year, month = map(int, month_year.split("-"))
    return calendar.monthrange(year, month)[1]


def _complete_months(df: pd.DataFrame, days_col: str) -> set[str]:
    """Return month_year values where the sum of days covers the full month."""
    monthly_days = df.groupby("month_year")[days_col].sum()
    return {
        m for m, d in monthly_days.items() if d >= _days_in_month(m)
    }


def compute_monthly_electricity_cost(
    flats_path: str = ".temp/monthly_flats_electricity.csv",
    building_path: str = ".temp/monthly_building_electricity.csv",
    output_path: str = ".temp/monthly_electricity_cost.csv",
) -> pd.DataFrame:
    flats = pd.read_csv(flats_path)
    building = pd.read_csv(building_path)

    # Only keep months fully covered by both sources
    complete_flats = _complete_months(flats, "number_day_reading_month")
    complete_building = _complete_months(building, "number_day")
    complete_months = complete_flats & complete_building

    flats = flats[flats["month_year"].isin(complete_months)]
    building = building[building["month_year"].isin(complete_months)]

    # Sum flats kwh_current per month
    current_cols = [f"{c}_current" for c in CONSUMERS]
    flats_monthly = flats.groupby("month_year")[current_cols].sum().reset_index()

    # Sum building cost per month
    building_monthly = (
        building.groupby("month_year")["cost"].sum().reset_index()
    )
    building_monthly = building_monthly.rename(columns={"cost": "total_cost"})

    # Join on complete months
    merged = pd.merge(flats_monthly, building_monthly, on="month_year", how="inner")

    # Compute total internal kwh
    merged["total_kwh"] = sum(merged[f"{c}_current"] for c in CONSUMERS)

    # Compute each consumer's cost share
    rows = []
    for _, row in merged.iterrows():
        entry = {
            "month_year": row["month_year"],
            "total_kwh": round(row["total_kwh"], 2),
            "total_cost": round(row["total_cost"], 2),
        }
        for c in CONSUMERS:
            cost_key = c.replace("kwh_", "cost_")
            if row["total_kwh"] > 0:
                entry[cost_key] = round(
                    row[f"{c}_current"] / row["total_kwh"] * row["total_cost"], 2
                )
            else:
                entry[cost_key] = 0.0
        rows.append(entry)

    result = pd.DataFrame(rows)
    result.to_csv(output_path, index=False)
    return result
