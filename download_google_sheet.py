"""
Download Google Sheet as pandas DataFrame
"""

import json
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread


def load_config(config_path='config.json'):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


def download_google_sheet(sheet_url, worksheet_name=None, credentials_file=None):
    """
    Download a Google Sheet and return as pandas DataFrame
    
    Parameters:
    -----------
    sheet_url : str
        The URL or ID of the Google Sheet
    worksheet_name : str, optional
        Name of the specific worksheet/tab to download. If None, downloads the first sheet.
    credentials_file : str, optional
        Path to the service account credentials JSON file
    
    Returns:
    --------
    pd.DataFrame
        The sheet data as a pandas DataFrame
    """
    # Define the scope
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    # Authenticate
    creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet
    if 'docs.google.com' in sheet_url:
        # Extract sheet ID from URL
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        spreadsheet = client.open_by_key(sheet_id)
    else:
        # Assume it's just the sheet ID
        spreadsheet = client.open_by_key(sheet_url)
    
    # Get the worksheet
    if worksheet_name:
        worksheet = spreadsheet.worksheet(worksheet_name)
    else:
        worksheet = spreadsheet.get_worksheet(0)  # First sheet
    
    # Get all values and convert to DataFrame
    data = worksheet.get_all_values()
    
    if not data:
        return pd.DataFrame()
    
    # Use first row as header
    df = pd.DataFrame(data[1:], columns=data[0])
    
    return df


def main():
    """Main function to run the script"""
    # Load configuration
    config = load_config()
    
    # Download the sheet
    df = download_google_sheet(
        sheet_url=config['sheet_url'],
        worksheet_name=config.get('worksheet_name'),
        credentials_file=config['credentials_file']
    )
    
    print(f"Downloaded sheet with shape: {df.shape}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # Optional: Save to CSV
    if config.get('output_csv'):
        df.to_csv(config['output_csv'], index=False)
        print(f"\nSaved to: {config['output_csv']}")
    
    return df


if __name__ == "__main__":
    df = main()
