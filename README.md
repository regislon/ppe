# ppe

Downloads all worksheets from a private Google Sheet as CSV files into `.temp/`.

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- A Google Cloud project with **Google Sheets API** and **Google Drive API** enabled

## Setup

### 1. Google Cloud OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Google Sheets API** and **Google Drive API**
3. Go to **APIs & Services > OAuth consent screen**, set up the consent screen and add your Google account as a test user
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**
5. Application type: **Desktop app**
6. Download the JSON and save it as `client_secret.json` in the project root

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure

Edit `config.json`:

```json
{
  "sheet_url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID",
  "worksheet_name": null,
  "output_csv": "output_sheet.csv"
}
```

- **sheet_url**: Full Google Sheets URL
- **worksheet_name**: Not used currently (all sheets are downloaded)
- **output_csv**: Not used currently (files go to `.temp/`)

## Usage

```bash
uv run python main.py
```

On first run, your browser will open for Google authentication. After signing in, a `token.json` is saved locally for subsequent runs.

Each worksheet is saved as a separate CSV file in `.temp/` (e.g. `.temp/Sheet1.csv`, `.temp/Sheet2.csv`).

## Project structure

```
├── main.py              # Main script
├── config.json          # Sheet URL configuration
├── client_secret.json   # OAuth credentials (not committed)
├── token.json           # Auth token (auto-generated, not committed)
├── .temp/               # Downloaded CSV files (not committed)
└── pyproject.toml       # Project dependencies
```




Here’s a cleaned-up version with spelling and minor grammar fixes, keeping your structure and meaning intact:

---

# Business logic for this project

## Electricity consumption accounting and billing system

The objective of the project is to create an accounting system for electricity within a building.

### Characteristics:

* There is only one bill from the electricity provider, which arrives a couple of times per year.
* This information is referenced in the file `.temp/electricite_romande_energie.csv`, which contains the following columns:

  * **Date facture**: billing date
  * **Montant facturé**: amount on the bill
  * **Électricité achetée [kWh]**: the number of kWh purchased from the provider
  * **Électricité vendue [kWh]**: the number of kWh sold to the provider (solar panels)
  * **Différence [kWh]**: the delta between purchased and sold electricity
  * **Début période**: start of the period (YYYY/MM/DD)
  * **Fin période**: end of the period (YYYY/MM/DD)
  * **Prix par kWh**: the delta divided by the amount of the bill → the cost per kWh



Inside the house, there are four electricity meters:

* **Rez supérieur**: supplies one flat
* **Rez inférieur**: supplies one flat
* **Commun**: supplies electricity for shared areas (outside any flat)
* **Congélateur**: supplies electricity for a single freezer

Meter readings are stored in the file `.temp/electricite_compteurs.csv`, which contains the following columns:

* **Date de relevé**: date on which the meter reading was recorded
* **Compteur commun [kWh]**: reading of the “commun” meter
* **Compteur rez inférieur [kWh]**: reading of the “rez inférieur” meter
* **Compteur rez supérieur [kWh]**: reading of the “rez supérieur” meter
* **Compteur  1er [kWh]**: reading of the “1er étage” meter
* **Compteur congélateur [kWh]**: reading of the “congélateur” meter

---

### Computation

#### Monthly building electricity

The goal is to create a table named `.temp/monthly_building_electricity.csv`, based on the source file `.temp/electricite_romande_energie.csv`.

The resulting table should contain the following columns:

* **billing_date**: taken from the source table
* **billing_amount**: taken from the source table
* **total_number_days**: total number of days in the billing period
* **month_year**: each month included in the billing period
* **kwh_price**: taken from the source table
* **number_day**: number of days in the billing period that fall within the given month (billing periods usually do not end on the last day of a month)
* **kwh**: electricity consumption allocated to the month, computed as
  `Différence [kWh] × number_day / total_number_days`
* **cost**: cost of electricity for this part of the month, computed as
  `kwh × kwh_price`

Raise an issue if there is gaps in `.temp/electricite_romande_energie.csv`. And stop the process in that case.  



#### Monthly flats electricity

The goal is to create a table named `.temp/monthly_flats_electricity.csv`, based on the source file `.temp/electricite_compteurs.csv`.

The resulting table should contain the following columns:

* **reading_date** : taken from the source table - attribute `Date de relevé`
* **total_number_days** : total number of day between the the previous reding and the current one 
* **month_year**: each month included in the reading period
* **number_day_reading_month** : number of day in the reading period and the month
* **kwh_0_total** : total kWh from the `Compteur rez inférieur [kWh]` column un the source table
* **kwh_0_current** : kwh for the current month / reading period for the `Compteur rez inférieur [kWh]`
* **kwh_1_total** : total kWh from the `Compteur rez supérieur [kWh]` column un the source table
* **kwh_1_current** : kwh for the current month / reading period for the `Compteur rez supérieur [kWh]`
* **kwh_2_total** : total kWh from the `Compteur  1er [kWh]` column un the source table
* **kwh_2_current** : kwh for the current month / reading period for the `Compteur  1er [kWh]`
* **kwh_fridge_total** : total kWh from the `Compteur congélateur [kWh]` column un the source table
* **kwh_fridge_current** : kwh for the current month / reading period for the `Compteur congélateur [kWh]`
* **kwh_building_total** : total kWh from the `Compteur commun [kWh]` column in the source table minus `kwh_fridge_total`
* **kwh_building_current** : kwh for the current month / reading period for the `Compteur commun [kWh]`  minus `kwh_fridge_total`

-> sort the rows by Date de relevé. 
-> raise an issue id not a valid date
-> raise an issue if the amount of kWh decrease. 


#### Monthly electricity cost

The goal is to create a table named `.temp/monthly_electricity_cost.csv` based on `.temp/monthly_flats_electricity.csv` and `.temp/monthly_building_electricity.csv`.

For each month, the total cost from the provider bill is distributed proportionally based on each consumer's share of the total internal consumption. The total internal consumption is the sum of all meters: `kwh_building_current + kwh_0_current + kwh_1_current + kwh_2_current + kwh_fridge_current`.

The formula for each consumer's cost is:
`consumer_cost = (consumer_kwh_current / total_internal_kwh_current) * cost`

Where `cost` comes from `.temp/monthly_building_electricity.csv`, grouped by month (sum).

Only months fully covered by both data sources are included. A month is considered complete when the sum of allocated days equals the number of days in that month, for both the billing periods and the meter reading periods. Incomplete months (e.g. the last reading falls mid-month) are excluded.

* **month_year**: each complete month covered by both the billing period and the reading period
* **total_kwh**: sum of all meters' `kwh_current` for the month
* **total_cost**: sum of `cost` from `.temp/monthly_building_electricity.csv` for the month
* **cost_building**: share of cost for `kwh_building_current` (common areas)
* **cost_0**: share of cost for `kwh_0_current` (rez inférieur)
* **cost_1**: share of cost for `kwh_1_current` (rez supérieur)
* **cost_2**: share of cost for `kwh_2_current` (1er)
* **cost_fridge**: share of cost for `kwh_fridge_current` (congélateur)



#### Cost allocation

The total electricity cost is split among the people living in the building. Each person pays for their flat's consumption plus a configurable share of the common areas and fridge costs.

The allocation is defined in `config.json` under the `persons` key. Each person has:
- **name**: full name (for billing)
- **address**: postal address (for billing)
- **flat_cost**: which flat cost column they pay (`cost_0`, `cost_1`, `cost_2`, or `null` if none)
- **building_share**: percentage of `cost_building` they pay (all shares must sum to 100)
- **fridge_share**: percentage of `cost_fridge` they pay (all shares must sum to 100)

Example with 3 people:
- Person 1 pays `cost_2` (1er) - no share of fridge or building
- Person 2 pays `cost_1` (rez supérieur) + a share of building + a share of fridge
- Person 3 pays `cost_0` (rez inférieur) + a share of building + a share of fridge
- Personn 4 pays a share of building


#### Billing 

Export one PDF per person per month inside the folder ./bills
if a bill for a given person and month done not rewite it 
In the bill explain the calcul, very pedogogically

