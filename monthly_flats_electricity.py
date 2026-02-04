import calendar
from datetime import date, timedelta

import pandas as pd


METER_COLUMNS = {
    "Compteur rez inférieur [kwh]": "kwh_0",
    "Compteur rez supérieur [kwh]": "kwh_1",
    "Compteur 1er [kwh]": "kwh_2",
    "Compteur congélateur [kWh]": "kwh_fridge",
}

COL_COMMUN = "Compteur commun [kWh]"


def compute_monthly_flats_electricity(
    source_path: str = ".temp/electricite_compteurs.csv",
    output_path: str = ".temp/monthly_flats_electricity.csv",
) -> pd.DataFrame:
    df = pd.read_csv(source_path)
    df.columns = df.columns.str.strip()

    # Filter out empty rows
    df = df.dropna(subset=["Date de relevé"]).reset_index(drop=True)
    df = df[df["Date de relevé"].astype(str).str.strip() != ""].reset_index(drop=True)

    df["_date"] = pd.to_datetime(df["Date de relevé"], dayfirst=True)
    df = df.sort_values("_date").reset_index(drop=True)

    rows = []
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        reading_date = curr["Date de relevé"]
        period_start = prev["_date"].date()
        period_end = curr["_date"].date()
        total_number_days = (period_end - period_start).days

        if total_number_days <= 0:
            raise ValueError(
                f"Reading dates are not strictly increasing: "
                f"{period_start} -> {period_end}"
            )

        # Compute total consumption per meter for this reading period
        totals = {}
        for src_col, dest_prefix in METER_COLUMNS.items():
            diff = float(curr[src_col]) - float(prev[src_col])
            if diff < 0:
                raise ValueError(
                    f"kWh decreased for '{src_col}': "
                    f"{prev[src_col]} ({period_start}) -> {curr[src_col]} ({period_end})"
                )
            totals[dest_prefix] = diff

        # kwh_building = commun minus fridge (fridge is on the commun circuit)
        commun_diff = float(curr[COL_COMMUN]) - float(prev[COL_COMMUN])
        if commun_diff < 0:
            raise ValueError(
                f"kWh decreased for '{COL_COMMUN}': "
                f"{prev[COL_COMMUN]} ({period_start}) -> {curr[COL_COMMUN]} ({period_end})"
            )
        totals["kwh_building"] = commun_diff - totals["kwh_fridge"]

        # Split into months (period is day after prev reading to current reading)
        month_start_date = period_start + timedelta(days=1)
        current = month_start_date
        while current <= period_end:
            first_of_month = date(current.year, current.month, 1)
            last_of_month = date(
                current.year,
                current.month,
                calendar.monthrange(current.year, current.month)[1],
            )

            seg_start = max(current, first_of_month)
            seg_end = min(last_of_month, period_end)
            number_day = (seg_end - seg_start).days + 1

            row_data = {
                "reading_date": reading_date,
                "total_number_days": total_number_days,
                "month_year": f"{current.year}-{current.month:02d}",
                "number_day_reading_month": number_day,
            }

            for dest_prefix, total_kwh in totals.items():
                row_data[f"{dest_prefix}_total"] = round(total_kwh, 2)
                row_data[f"{dest_prefix}_current"] = round(
                    total_kwh * number_day / total_number_days, 2
                )

            rows.append(row_data)

            # Move to first day of next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    result = pd.DataFrame(rows)
    result.to_csv(output_path, index=False)
    return result
