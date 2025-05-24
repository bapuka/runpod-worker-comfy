from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

from googleapiclient.errors import HttpError
import json
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']

def upload_images_to_shared_drive(service_account_file, drive_id, folder_id, image_directory):
    """
    Upload multiple images to a folder in a Shared Drive
    
    Args:
        service_account_file: Path to service account JSON key file
        drive_id: ID of the Shared Drive
        folder_id: ID of the folder within the Shared Drive
        image_directory: Directory containing images to upload
    """
    # Set up credentials
    # SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    
    # Build the Drive service
    service = build('drive', 'v3', credentials=credentials)
    
    # Print service account info for debugging
    with open(service_account_file, 'r') as f:
        service_account_info = json.load(f)
    print(f"Using service account: {service_account_info.get('client_email')}")
    
    # First, verify the Shared Drive exists and is accessible
    try:
        drive = service.drives().get(driveId=drive_id).execute()
        print(f"Found Shared Drive: {drive.get('name')}")
    except HttpError as error:
        print(f"Error accessing Shared Drive: {error}")
        return []

    # Next, verify the folder exists within the Shared Drive
    try:
        # When querying files in a Shared Drive, we need to use the files.list method
        # with the correct parameters
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            driveId=drive_id,
            corpora='drive',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="files(id, name)"
        ).execute()
        
        # Just testing if we can list files in the target folder
        items = results.get('files', [])
        print(f"Found {len(items)} existing files in target folder")
        
        # Now try to get the folder itself to verify it exists
        folder = service.files().get(
            fileId=folder_id, 
            supportsAllDrives=True,
            fields="id,name,mimeType"
        ).execute()
        
        print(f"Target folder verified: {folder.get('name')} ({folder_id})")
        
    except HttpError as error:
        print(f"Error verifying folder in Shared Drive: {error}")
        if error.resp.status == 404:
            print("The folder ID doesn't exist or your service account doesn't have access to it")
        return []
    
    # List image files from the local directory
    if not os.path.exists(image_directory):
        print(f"Error: Image directory {image_directory} does not exist")
        return []
    
    image_files = [f for f in os.listdir(image_directory) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    
    if not image_files:
        print(f"No image files found in {image_directory}")
        return []
    
    print(f"Found {len(image_files)} images to upload")
    
    uploaded_files = []
    
    # Upload each image
    for image_file in image_files:
        file_path = os.path.join(image_directory, image_file)
        
        # Define file metadata
        file_metadata = {
            'name': image_file,
            'parents': [folder_id],
            # This is important - makes sure the file is created in the Shared Drive
            'driveId': drive_id
        }
        
        # Create media file upload
        media = MediaFileUpload(file_path, resumable=True)
        
        try:
            # Execute the upload with parameters required for Shared Drives
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name',
                supportsAllDrives=True,  # Critical for Shared Drives
            ).execute()
            
            uploaded_files.append({'name': image_file, 'id': file.get('id')})
            print(f"Successfully uploaded {image_file} with file ID {file.get('id')}")
            
        except HttpError as error:
            print(f"Error uploading {image_file}: {error}")
    
    return uploaded_files

# Function to find the driveId for a Shared Drive by name
def find_shared_drive_id(service_account_file, drive_name):
    """Find a Shared Drive ID by its name"""
    # SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    
    service = build('drive', 'v3', credentials=credentials)
    
    try:
        drives = []
        page_token = None
        
        while True:
            response = service.drives().list(
                pageSize=100,
                pageToken=page_token
            ).execute()
            
            drives.extend(response.get('drives', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
        
        for drive in drives:
            if drive.get('name') == drive_name:
                drive_id = drive.get('id')
                print(f"Found Shared Drive: {drive_name} with ID: {drive_id}")
                return drive_id
        
        print(f"Could not find Shared Drive with name: {drive_name}")
        return None
        
    except HttpError as error:
        print(f"Error listing Shared Drives: {error}")
        return None

# Function to find a folder within a Shared Drive
def find_folder_in_shared_drive(service_account_file, drive_id, folder_name, parent_folder_id=None):
    """Find a folder by name within a Shared Drive"""
    # SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    
    service = build('drive', 'v3', credentials=credentials)
    
    try:
        # Build query to find the folder
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        
        # Add folder name to query
        query += f" and name = '{folder_name}'"
        
        # If parent folder is specified, search within that folder
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
            
        results = service.files().list(
            q=query,
            driveId=drive_id,
            corpora='drive',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="files(id, name, parents)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print(f"No folder named '{folder_name}' found in the Shared Drive")
            return None
        
        # If multiple folders with the same name exist, return the first one
        folder_id = items[0].get('id')
        print(f"Found folder: {folder_name} with ID: {folder_id}")
        return folder_id
        
    except HttpError as error:
        print(f"Error finding folder: {error}")
        return None

def create_folder_path(service, parent_folder_id, folder_path):
    """
    Create a nested folder structure in Google Drive
    
    Args:
        service: Google Drive API service instance
        parent_folder_id: ID of the parent folder to create the path under
        folder_path: Path string like "book-15/chapter-1"
    
    Returns:
        ID of the deepest folder created
    """
    # Split the path into folder names
    folder_names = folder_path.split('/')
    current_parent_id = parent_folder_id
    
    # Create each folder in the path if it doesn't exist
    for folder_name in folder_names:
        # Check if folder already exists
        query = f"name = '{folder_name}' and '{current_parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            # Folder exists, use it as the parent for the next level
            current_parent_id = items[0]['id']
            print(f"Found existing folder: {folder_name} ({current_parent_id})")
        else:
            # Folder doesn't exist, create it
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [current_parent_id]
            }
            
            folder = service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            current_parent_id = folder.get('id')
            print(f"Created new folder: {folder_name} ({current_parent_id})")
    
    return current_parent_id

def find_folder_by_name(service, folder_name):
    """
    Find a folder by name in Google Drive
    
    Args:
        service: Google Drive API service instance
        folder_name: Name of the folder to find
    
    Returns:
        ID of the folder if found, None otherwise
    """
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        return None
    
def get_credentials_from_file(service_account_file):
    """
    Get Google Drive API credentials from a service account file
    
    Args:
        service_account_file: Path to the service account JSON key file
    
    Returns:
        Google Drive API credentials
    """
    
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES)
    
    return credentials

def get_credentials_from_env():
    """
    Get Google Drive API credentials from environment variables
    
    Returns:
        Google Drive API credentials
    """
    
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
    
    # Parse the JSON
    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    
    # Create credentials from the parsed info    
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    
    return credentials

def upload_image_to_drive(folder_id, image_path, folder_path=None):
    """
    Upload multiple images to a Google Drive folder
    
    Args:
        service_account_file: Path to service account JSON key file
        folder_id: ID of the Google Drive folder to upload to (should be "DT | Booky" folder)
        image_directory: Directory containing images to upload
        folder_path: Optional path like "book-15/chapter-1" to create under the folder_id
    
    Returns:
        List of uploaded file information
    """
    # Set up credentials
    
    # credentials = service_account.Credentials.from_service_account_file(
    #     service_account_file, scopes=SCOPES)
    credentials = get_credentials_from_env()
    
    # Build the Drive service
    service = build('drive', 'v3', credentials=credentials)
    
    # Find the "DT | Booky" folder if folder_id is not provided
    if not folder_id:
        folder_id = find_folder_by_name(service, "DT | Booky")
        if not folder_id:
            print("Error: Could not find 'DT | Booky' folder")
            return []
        print(f"Found 'DT | Booky' folder with ID: {folder_id}")
    
    # Create folder path if provided
    target_folder_id = folder_id
    if folder_path:
        target_folder_id = create_folder_path(service, folder_id, folder_path)
        print(f"Using target folder ID: {target_folder_id}")
           
    # print(f"Found {len(image_files)} images to upload")
    
    file_metadata = {
            'name': image_path[image_path.rindex('/') + 1:],  # Get the file name from the path
            'parents': [target_folder_id]
        }
        
    # Create media file upload
    media = MediaFileUpload(image_path, resumable=True)
        
    try:
        # Execute the upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name',
            supportsAllDrives=True
        ).execute()
            
        # uploaded_files.append({'name': image_file, 'id': file.get('id')})
        print(f"Successfully uploaded {image_path} with file ID {file.get('id')}")
            
    except HttpError as error:
        print(f"Error uploading {image_path}: {error}")
        return False
    
    return True
