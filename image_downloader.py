import os
import tkinter as tk
from tkinter import ttk, messagebox
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# Define the root Google Drive folder ID
ROOT_FOLDER_ID = "1tveP4qft85NmTwqJZGzHZcHhtSqHWyuW"  # Replace with your actual Drive root folder ID
LOCAL_PATH = "C:/Anchor/Pharmacy Data"

# Function to get folder ID by name
def get_folder_id(parent_id, folder_name):
    file_list = drive.ListFile({'q': f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    for file in file_list:
        if file['title'] == folder_name:
            return file['id']
    return None

# Function to download images
def download_images():
    selected_month = month_var.get()
    selected_pharmacy = pharmacy_var.get()
    
    if not selected_month or not selected_pharmacy:
        messagebox.showerror("Error", "Please select both month and pharmacy.")
        return
    
    month_folder_id = get_folder_id(ROOT_FOLDER_ID, selected_month)
    if not month_folder_id:
        messagebox.showerror("Error", f"Month folder '{selected_month}' not found on Google Drive.")
        return
    
    pharmacy_folder_id = get_folder_id(month_folder_id, selected_pharmacy)
    if not pharmacy_folder_id:
        messagebox.showerror("Error", f"Pharmacy folder '{selected_pharmacy}' not found in '{selected_month}'.")
        return
    
    local_folder = os.path.join(LOCAL_PATH, selected_month, selected_pharmacy)
    os.makedirs(local_folder, exist_ok=True)
    
    file_list = drive.ListFile({'q': f"'{pharmacy_folder_id}' in parents and trashed=false"}).GetList()
    total_files = len(file_list)
    
    progress_var.set(0)
    progress_bar['maximum'] = total_files
    
    for index, file in enumerate(file_list):
        file_path = os.path.join(local_folder, file['title'])
        file.GetContentFile(file_path)
        print(f"Downloaded: {file['title']} -> {file_path}")
        progress_var.set(index + 1)
        root.update_idletasks()
    
    messagebox.showinfo("Success", f"Images downloaded to: {local_folder}")

# UI Setup
root = tk.Tk()
root.title("Google Drive Image Downloader")
root.geometry("400x250")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

month_var = tk.StringVar()
pharmacy_var = tk.StringVar()
progress_var = tk.IntVar()

ttk.Label(frame, text="Select Month:").grid(row=0, column=0, padx=5, pady=5)
month_dropdown = ttk.Combobox(frame, textvariable=month_var, values=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], state="readonly")
month_dropdown.grid(row=0, column=1, padx=5, pady=5)

pharmacy_values = [f"Pharmacy {i}" for i in range(1, 16)]
ttk.Label(frame, text="Select Pharmacy:").grid(row=1, column=0, padx=5, pady=5)
pharmacy_dropdown = ttk.Combobox(frame, textvariable=pharmacy_var, values=pharmacy_values, state="readonly")
pharmacy_dropdown.grid(row=1, column=1, padx=5, pady=5)

run_button = ttk.Button(frame, text="Download Images", command=download_images)
run_button.grid(row=2, column=0, columnspan=2, pady=10)

progress_bar = ttk.Progressbar(frame, variable=progress_var, mode='determinate')
progress_bar.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))

root.mainloop()
