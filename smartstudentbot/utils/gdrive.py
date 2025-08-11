import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import GOOGLE_DRIVE_CREDS, GOOGLE_DRIVE_UPLOAD_FOLDER_ID

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_gdrive_service():
    """Initializes and returns the Google Drive API service."""
    if not GOOGLE_DRIVE_CREDS or not os.path.exists(GOOGLE_DRIVE_CREDS):
        print("Warning: Google Drive credentials not found. File upload will be disabled.")
        return None

    creds = Credentials.from_service_account_file(GOOGLE_DRIVE_CREDS, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_file_to_drive(file_path: str, file_name: str, mime_type: str) -> str | None:
    """
    Uploads a file to a specific Google Drive folder and returns the web view link.

    Args:
        file_path: The local path to the file to upload.
        file_name: The name the file should have in Google Drive.
        mime_type: The MIME type of the file.

    Returns:
        The web link to the uploaded file, or None if upload fails.
    """
    service = get_gdrive_service()
    if not service or not GOOGLE_DRIVE_UPLOAD_FOLDER_ID:
        return None

    try:
        file_metadata = {
            'name': file_name,
            'parents': [GOOGLE_DRIVE_UPLOAD_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype=mime_type)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        print(f"File '{file_name}' uploaded successfully. File ID: {file.get('id')}")
        return file.get('webViewLink')

    except Exception as e:
        print(f"An error occurred during Google Drive upload: {e}")
        return None
