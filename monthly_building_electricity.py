import calendar
from datetime import date

import pandas as pd


def parse_chf(value: str) -> float:
    if not value or not isinstance(value, str):
        return 0.0
    return float(value.replace("CHF", "").replace(",", "").strip())


def compute_monthly_building_electricity(
    source_path: str = ".temp/electricite_romande_energie.csv",
    output_path: str = ".temp/monthly_building_electricity.csv",
) -> pd.DataFrame:
    df = pd.read_csv(source_path)

    # Filter out empty rows
    df = df.dropna(subset=["Date facture"]).reset_index(drop=True)
    df = df[df["Date facture"].str.strip() != ""].reset_index(drop=True)

    # Handle typo in column name
    end_col = [c for c in df.columns if c.startswith("Fin p")][0]

    rows = []
    for _, row in df.iterrows():
        billing_date = row["Date facture"]
        billing_amount = parse_chf(str(row["Montant facturé"]))
        difference_kwh = float(row["Différence [kWh]"])
        kwh_price = parse_chf(str(row["Prix par kWh"]))

        start = pd.to_datetime(row["Début période"], dayfirst=True).date()
        end = pd.to_datetime(row[end_col], dayfirst=True).date()

        total_number_days = (end - start).days + 1

        # Iterate over each month in the billing period
        current = start
        while current <= end:
            month_start = date(current.year, current.month, 1)
            month_end = date(
                current.year,
                current.month,
                calendar.monthrange(current.year, current.month)[1],
            )

            # Clamp to billing period
            period_start = max(current if current == start else month_start, start)
            period_end = min(month_end, end)

            number_day = (period_end - period_start).days + 1
            kwh = difference_kwh * number_day / total_number_days
            cost = kwh * kwh_price

            rows.append(
                {
                    "billing_date": billing_date,
                    "billing_amount": billing_amount,
                    "total_number_days": total_number_days,
                    "month_year": f"{current.year}-{current.month:02d}",
                    "kwh_price": kwh_price,
                    "number_day": number_day,
                    "kwh": round(kwh, 2),
                    "cost": round(cost, 2),
                }
            )

            # Move to first day of next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    result = pd.DataFrame(rows)
    result.to_csv(output_path, index=False)
    return result
