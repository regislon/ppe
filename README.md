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
* **Compteur congélateur [kWh]**: reading of the “congélateur” meter

---

### Computation

#### Monthly building electricity

The goal is to create a table named `.temp/monthly_building_electricity.csv`, based on the source file `.temp/electricite_romande_energie.csv`.

The resulting table should contain the following columns:

* **billing_date**: taken from the source table
* **billing_amount**: taken from the source table
* **total_number_days**: total number of days in the billing period
* **month_year**: each month fully included in the billing period
* **kwh_price**: taken from the source table
* **number_day**: number of days in the billing period that fall within the given month (billing periods usually do not end on the last day of a month)
* **kwh**: electricity consumption allocated to the month, computed as
  `Différence [kWh] × number_day / total_number_days`
* **cost**: cost of electricity for this part of the month, computed as
  `kwh × kwh_price`


