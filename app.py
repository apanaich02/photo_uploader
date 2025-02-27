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

    # Load client_secrets.json from Render's environment variables
    client_secrets_content = os.getenv("CLIENT_SECRETS_JSON")
    my_creds_content = os.getenv("MYCREDS_TXT")

    if not client_secrets_content:
        raise Exception("CLIENT_SECRETS_JSON is missing from environment variables.")

    if not my_creds_content:
        raise Exception("MYCREDS_TXT is missing from environment variables.")

    # Write client_secrets.json locally
    with open("client_secrets.json", "w") as f:
        f.write(client_secrets_content)

    # Write mycreds.txt locally
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
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Anchor Delivery - Upload</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                background-color: #f4f4f4;
                color: #333;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 400px;
                margin: auto;
                padding: 20px;
                background: white;
                border-radius: 10px;
                box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            }
            .logo {
                max-width: 200px;
                margin-bottom: 15px;
            }
            h2 {
                font-size: 22px;
                color: #007bff;
            }
            input, select, button {
                width: 100%;
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 16px;
            }
            input[type="file"] {
                border: none;
                background: #e3e3e3;
            }
            button {
                background-color: #007bff;
                color: white;
                border: none;
                cursor: pointer;
            }
            button:hover {
                background-color: #0056b3;
            }
            #progressContainer {
                display: none;
                margin-top: 10px;
                width: 100%;
            }
            #progressBar {
                width: 0%;
                height: 10px;
                background-color: #007bff;
                border-radius: 5px;
            }
            #popup {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .popup-content {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 300px;
            }
            .popup-content button {
                margin-top: 10px;
                width: 100%;
            }
            @media (prefers-color-scheme: dark) {
                body {
                    background-color: #1e1e1e;
                    color: white;
                }
                .container {
                    background: #333;
                    color: white;
                }
                input, select {
                    background: #444;
                    color: white;
                    border: 1px solid #666;
                }
                button {
                    background-color: #0d6efd;
                }
                .popup-content {
                    background: #444;
                    color: white;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <img src="/static/logo.png" alt="Anchor Delivery Logo" class="logo">
            <h2>Upload a Delivery Photo</h2>
            <form id='uploadForm' action='/upload' method='post' enctype='multipart/form-data' onsubmit='return uploadFile()'>
                
                <label for='file'>Take a Picture:</label>
                <input type='file' accept='image/*' capture='camera' name='file' required>

                <label for='pharmacy'>Select Pharmacy:</label>
                <select name='pharmacy' id='pharmacy' required>
                    <option value=''>--Select a Pharmacy--</option>
                    ''' + ''.join([f"<option value='Pharmacy {i}'>Pharmacy {i}</option>" for i in range(1, 16)]) + '''
                </select>

                <label for='rate'>Select Rate:</label>
                <select name='rate' id='rate' required>
                    <option value=''>--Select a Rate--</option>
                    <option value='ECO'>ECO</option>
                    <option value='REG'>REG</option>
                    <option value='HOT'>HOT</option>
                    <option value='RSH'>RSH</option>
                    <option value='SHT'>SHT</option>
                </select>

                <button type='submit'>Upload</button>
            </form>

            <div id="progressContainer">
                <div id="progressBar"></div>
            </div>
        </div>

        <div id="popup">
            <div class="popup-content">
                <p id="popupMessage"></p>
                <button onclick="closePopup()">OK</button>
            </div>
        </div>

        <script>
            function uploadFile() {
                var formData = new FormData(document.getElementById('uploadForm'));
                var selectedPharmacy = document.getElementById('pharmacy').value;
                var selectedRate = document.getElementById('rate').value;
                
                document.getElementById("progressContainer").style.display = "block";
                var progressBar = document.getElementById("progressBar");
                progressBar.style.width = "0%";

                var uploadTime = 5000; // Estimated upload time (5 seconds)
                var startTime = Date.now();

                var progressInterval = setInterval(function() {
                    var elapsedTime = Date.now() - startTime;
                    var progress = Math.min((elapsedTime / uploadTime) * 100, 100);
                    progressBar.style.width = progress + "%";
                    
                    if (progress >= 100) {
                        clearInterval(progressInterval);
                    }
                }, 500);

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(data => {
                    clearInterval(progressInterval);
                    progressBar.style.width = "100%";
                    showPopup(data);
                    document.getElementById('uploadForm').reset();
                    document.getElementById('pharmacy').value = selectedPharmacy;
                    document.getElementById('rate').value = selectedRate;
                })
                .catch(error => {
                    clearInterval(progressInterval);
                    showPopup("Upload failed. Please try again.");
                    console.error('Error:', error);
                });
                return false;
            }

            function showPopup(message) {
                document.getElementById("popupMessage").innerText = message;
                document.getElementById("popup").style.display = "flex";
            }

            function closePopup() {
                document.getElementById("popup").style.display = "none";
                document.getElementById("progressContainer").style.display = "none";
            }
        </script>
    </body>
    </html>
    '''

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

# Function to prevent Render from sleeping
def prevent_sleep():
    while True:
        try:
            url = "https://flask-photo-upload.onrender.com/"  # Change to your actual Render app URL
            response = requests.get(url)
            print(f"Self-ping successful: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")
        time.sleep(600)  # Sleep for 10 minutes

# Start self-ping in a background thread
threading.Thread(target=prevent_sleep, daemon=True).start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)