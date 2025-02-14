import json
import os
import datetime
import threading
import time
import requests
from flask import Flask, request
from werkzeug.utils import secure_filename
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB file size limit

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Google Drive Authentication
def authenticate_drive():
    gauth = GoogleAuth()

    # Load credentials from environment variables
    client_secrets_content = os.getenv("CLIENT_SECRETS_JSON")
    my_creds_content = os.getenv("MYCREDS_TXT")

    if not client_secrets_content:
        raise Exception("CLIENT_SECRETS_JSON is missing from environment variables.")

    if not my_creds_content:
        raise Exception("MYCREDS_TXT is missing from environment variables.")

    # Write credentials locally for PyDrive
    with open("client_secrets.json", "w") as f:
        f.write(client_secrets_content)

    with open("mycreds.txt", "w") as f:
        f.write(my_creds_content)

    # Authenticate Google Drive
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    
    return GoogleDrive(gauth)

# Initialize Google Drive Authentication
drive = authenticate_drive()

# Function to find or create a folder in Google Drive
def get_drive_folder(parent_id, folder_name):
    file_list = drive.ListFile({
        'q': f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    for file in file_list:
        if file['title'] == folder_name:
            return file['id']

    folder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_id}]
    })
    folder.Upload()
    return folder['id']

# Define the root Google Drive folder where all images will be stored
ROOT_FOLDER_ID = "1tveP4qft85NmTwqJZGzHZcHhtSqHWyuW"  # Change this to your main Drive folder ID

@app.route('/')
def index():
    return "Server is running."

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files or 'pharmacy' not in request.form or 'rate' not in request.form:
        return 'Missing required fields'

    file = request.files['file']
    pharmacy = request.form['pharmacy'].strip()
    rate = request.form['rate'].strip()

    if file.filename == '':
        return 'No selected file'

    # Get the current date
    current_date = datetime.datetime.now()
    month_folder = current_date.strftime("%B")
    formatted_date = current_date.strftime("%Y-%m-%d")

    # Construct the filename
    filename = secure_filename(f"{pharmacy}_{formatted_date}_{rate}.jpg")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get or create the month folder in Google Drive
    month_folder_id = get_drive_folder(ROOT_FOLDER_ID, month_folder)
    # Get or create the pharmacy folder inside the month folder
    pharmacy_folder_id = get_drive_folder(month_folder_id, pharmacy)

    # Upload the file to Google Drive inside the correct pharmacy folder
    gfile = drive.CreateFile({'title': filename, 'parents': [{'id': pharmacy_folder_id}]})
    gfile.SetContentFile(filepath)
    gfile.Upload()

    return f'File successfully uploaded to Google Drive in {month_folder}/{pharmacy} as {filename}'

# Function to keep the server alive by pinging itself every 10 minutes
def keep_alive():
    while True:
        try:
            print("Pinging the server to keep it awake...")
            requests.get("https://photo-uploader.onrender.com")  # Change this to your Render URL
        except requests.exceptions.RequestException as e:
            print(f"Ping failed: {e}")
        time.sleep(600)  # Wait for 10 minutes (600 seconds)

# Start the keep-alive thread
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
