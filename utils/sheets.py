import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Path to your downloaded service account JSON file
SERVICE_ACCOUNT_FILE = "service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def fetch_sheet_data(sheet_name, worksheet_name):
    # Create credentials from service account file
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    # Authorize gspread with service account
    gc = gspread.authorize(creds)

    # Open sheet
    sheet = gc.open(sheet_name).worksheet(worksheet_name)

    # Fetch records
    rows = sheet.get_all_records()

    return pd.DataFrame(rows)