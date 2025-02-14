from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Opens a web browser for authentication
gauth.SaveCredentialsFile("mycreds.txt")  # Saves new credentials
