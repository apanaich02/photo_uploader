import json
import os
from io import StringIO
from flask import Flask, request
import datetime
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

    client_secrets_content = os.getenv("CLIENT_SECRETS_JSON")
    my_creds_content = os.getenv("MYCREDS_TXT")

    if client_secrets_content:
        with open("client_secrets.json", "w") as f:
            f.write(client_secrets_content)

    if my_creds_content:
        with open("mycreds.txt", "w") as f:
            f.write(my_creds_content)

    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

# Function to find or create a folder in Google Drive
def get_drive_folder(parent_id, folder_name):
    file_list = drive.ListFile({'q': f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for file in file_list:
        if file['title'] == folder_name:
            return file['id']
    
    folder = drive.CreateFile({'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [{'id': parent_id}]})
    folder.Upload()
    return folder['id']

# Define the root Google Drive folder where all images will be stored
ROOT_FOLDER_ID = "1tveP4qft85NmTwqJZGzHZcHhtSqHWyuW"  # Change this to your main Drive folder ID

@app.route('/')
def index():
    return '''
    <html>
    <body>
        <h2>Take a Picture, Select a Pharmacy and Rate, and Upload</h2>
        <form id='uploadForm' action='/upload' method='post' enctype='multipart/form-data' onsubmit='return uploadFile()'>
            <label for='file'>Take a Picture:</label>
            <input type='file' accept='image/*' capture='camera' name='file' required>
            <br><br>

            <label for='pharmacy'>Select Pharmacy:</label>
            <select name='pharmacy' id='pharmacy' required>
                <option value=''>--Select a Pharmacy--</option>
                <option value='Pharmacy 1'>Pharmacy 1</option>
                <option value='Pharmacy 2'>Pharmacy 2</option>
                <option value='Pharmacy 3'>Pharmacy 3</option>
                <option value='Pharmacy 4'>Pharmacy 4</option>
                <option value='Pharmacy 5'>Pharmacy 5</option>
                <option value='Pharmacy 6'>Pharmacy 6</option>
                <option value='Pharmacy 7'>Pharmacy 7</option>
                <option value='Pharmacy 8'>Pharmacy 8</option>
                <option value='Pharmacy 9'>Pharmacy 9</option>
                <option value='Pharmacy 10'>Pharmacy 10</option>
                <option value='Pharmacy 11'>Pharmacy 11</option>
                <option value='Pharmacy 12'>Pharmacy 12</option>
                <option value='Pharmacy 13'>Pharmacy 13</option>
                <option value='Pharmacy 14'>Pharmacy 14</option>
                <option value='Pharmacy 15'>Pharmacy 15</option>
            </select>
            <br><br>

            <label for='rate'>Select Rate:</label>
            <select name='rate' id='rate' required>
                <option value=''>--Select a Rate--</option>
                <option value='ECO'>ECO</option>
                <option value='REG'>REG</option>
                <option value='HOT'>HOT</option>
                <option value='RSH'>RSH</option>
                <option value='SHT'>SHT</option>
            </select>
            <br><br>

            <input type='submit' value='Send'>
        </form>

        <script>
            function uploadFile() {
                var formData = new FormData(document.getElementById('uploadForm'));
                var selectedPharmacy = document.getElementById('pharmacy').value;
                var selectedRate = document.getElementById('rate').value;
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(data => {
                    alert(data); // Show popup confirmation
                    document.getElementById('uploadForm').reset(); // Reset form
                    document.getElementById('pharmacy').value = selectedPharmacy; // Keep previous selection
                    document.getElementById('rate').value = selectedRate; // Keep previous selection
                })
                .catch(error => console.error('Error:', error));
                return false;
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

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
