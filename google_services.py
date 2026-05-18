"""
google_services.py
Handles Google Sheets logging and Google Drive PDF archiving.
Uses free Google APIs with service account credentials.
"""

import os
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

CREDENTIALS_FILE = "credentials.json"


def get_credentials():
    """Load service account credentials from credentials.json."""
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"credentials.json not found. Please add it to the project root.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        return creds
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return None


def log_lead_to_sheets(lead_data: dict, report_status: str = "Success") -> bool:
    """
    Append a new lead row to Google Sheets.
    Columns: Name | Email | Company | Website | Industry | Timestamp | Report Status
    Returns True on success.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        logger.error("GOOGLE_SHEET_ID not set in .env")
        return False

    creds = get_credentials()
    if not creds:
        return False

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        full_name = f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}".strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            full_name,
            lead_data.get("email", ""),
            lead_data.get("company_name", ""),
            lead_data.get("website", ""),
            lead_data.get("industry", ""),
            lead_data.get("company_size", ""),
            lead_data.get("phone", ""),
            lead_data.get("challenge", ""),
            lead_data.get("source", ""),
            timestamp,
            report_status,
        ]

        result = sheet.values().append(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        logger.info(f"Lead logged to Google Sheets: {full_name} ({lead_data.get('email', '')})")
        return True

    except Exception as e:
        logger.error(f"Failed to log to Google Sheets: {e}")
        return False


def setup_sheet_headers() -> bool:
    """
    Add header row to the Google Sheet if it's empty.
    Call this once when setting up the project.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return False

    creds = get_credentials()
    if not creds:
        return False

    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()

        # Check if headers already exist
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range="Sheet1!A1:K1"
        ).execute()

        values = result.get("values", [])
        if values:
            logger.info("Headers already exist in sheet.")
            return True

        # Add headers
        headers = [[
            "Full Name", "Email", "Company", "Website", "Industry",
            "Company Size", "Phone", "Challenge", "Source",
            "Timestamp", "Report Status"
        ]]

        sheet.values().update(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="USER_ENTERED",
            body={"values": headers}
        ).execute()

        # Format headers (bold, background)
        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 11
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.42, "green": 0.39, "blue": 1.0},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        }]
        sheet.batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests}
        ).execute()

        logger.info("Sheet headers added successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to setup sheet headers: {e}")
        return False


def upload_pdf_to_drive(pdf_path: str, company_name: str) -> str | None:
    """
    Upload a PDF to Google Drive folder.
    Returns the shareable link on success, None on failure.
    """
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.error("GOOGLE_DRIVE_FOLDER_ID not set in .env")
        return None

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return None

    creds = get_credentials()
    if not creds:
        return None

    try:
        service = build("drive", "v3", credentials=creds)

        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{company_name} — Audit Report {timestamp}.pdf"

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
            "mimeType": "application/pdf",
        }

        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        file_id = file.get("id")
        view_link = file.get("webViewLink", "")

        # Make it readable by anyone with link (optional)
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        logger.info(f"PDF uploaded to Drive: {filename} — {view_link}")
        return view_link

    except Exception as e:
        logger.error(f"Failed to upload to Drive: {e}")
        return None