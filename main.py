import json
import os
import re

import gspread
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from monthly_building_electricity import compute_monthly_building_electricity
from monthly_flats_electricity import compute_monthly_flats_electricity

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def load_config(config_path: str = "config.json") -> dict:
    with open(config_path) as f:
        return json.load(f)


def extract_sheet_id(sheet_url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError(f"Could not extract sheet ID from URL: {sheet_url}")
    return match.group(1)


def get_credentials() -> Credentials:
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"'{CLIENT_SECRET_FILE}' not found.\n"
                    "Download it from Google Cloud Console:\n"
                    "  1. Go to https://console.cloud.google.com/\n"
                    "  2. APIs & Services > Credentials\n"
                    "  3. Create Credentials > OAuth client ID > Desktop app\n"
                    "  4. Download the JSON and save it as 'client_secret.json'"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def download_all_sheets(
    sheet_url: str,
    creds: Credentials,
    output_dir: str = ".temp",
) -> dict[str, pd.DataFrame]:
    client = gspread.authorize(creds)

    sheet_id = extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)

    os.makedirs(output_dir, exist_ok=True)

    dataframes = {}
    for worksheet in spreadsheet.worksheets():
        name = worksheet.title
        print(f"  Downloading '{name}'...")
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        dataframes[name] = df

        csv_path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(csv_path, index=False)

    return dataframes


def main():
    config = load_config()

    creds = get_credentials()

    print(f"Downloading sheet: {config['sheet_url']}")
    dataframes = download_all_sheets(config["sheet_url"], creds)
    print(f"Downloaded {len(dataframes)} sheet(s) to ./.temp/")

    print("\nComputing monthly_building_electricity...")
    result = compute_monthly_building_electricity()
    print(f"Saved to .temp/monthly_building_electricity.csv ({len(result)} rows)")

    print("\nComputing monthly_flats_electricity...")
    result = compute_monthly_flats_electricity()
    print(f"Saved to .temp/monthly_flats_electricity.csv ({len(result)} rows)")


if __name__ == "__main__":
    main()
