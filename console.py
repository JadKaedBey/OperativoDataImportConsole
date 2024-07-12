import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import pandas as pd
from pymongo import MongoClient
from math import floor
import os

# Initialize global variable
queued_df = pd.DataFrame()
client = None  # Initialize client variable
login_logo = Image.open(r".\OPERATIVO_L_Main_Color.png")
login_logo_width = 1654
login_logo_length = 1246

original_logo = Image.open(r".\OPERATIVO_L_Main_Color.png") 
original_logo_width = 1654
original_logo_length = 1246

window_width = 1400
window_height = 800

# Function to connect to MongoDB
def connect_to_mongodb(username, password):
    global client
    # Add your logic to connect to different MongoDB clusters based on username and password
    if username == "user1" and password == "password1":
        client = MongoClient('mongodb+srv://michael:stegish@jadclu-ster.d4ppdse.mongodb.net/')
    elif username == "user2" and password == "password2":
        client = MongoClient('mongodb+srv://michael:stegish@jadclu-ster.d4ppdse.mongodb.net/')
    else:
        return False
    return True

# Function to show login window
def show_login():
    
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    login_window = tk.Toplevel(root)
    login_window.title("Login")

    # Load and resize the image for the login window
    
    resized_login_logo = login_logo.resize((floor(login_logo_width/6), floor(login_logo_length/6)), Image.Resampling.LANCZOS)
    login_logo_img = ImageTk.PhotoImage(resized_login_logo)
    logo_label = tk.Label(login_window, image=login_logo_img)
    logo_label.image = login_logo_img  # Keep a reference!
    logo_label.grid(row=0, column=0, columnspan=2, pady=10)

    tk.Label(login_window, text="Username:", font=("Proxima Nova", 12)).grid(row=1, column=0, padx=10, pady=10)
    username_entry = tk.Entry(login_window, font=("Proxima Nova", 12))
    username_entry.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(login_window, text="Password:", font=("Proxima Nova", 12)).grid(row=2, column=0, padx=10, pady=10)
    password_entry = tk.Entry(login_window, show="*", font=("Proxima Nova", 12))
    password_entry.grid(row=2, column=1, padx=10, pady=10)

    def on_login():
        username = username_entry.get()
        password = password_entry.get()
        if connect_to_mongodb(username, password):
            login_window.destroy()
            root.deiconify()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    tk.Button(login_window, text="Login", command=on_login, font=("Proxima Nova", 12)).grid(row=3, column=0, columnspan=2, pady=10)

    # Center the login window
    login_window.update_idletasks()
    login_width = login_window.winfo_width()
    login_height = login_window.winfo_height()
    login_x = (screen_width // 2) - (login_width // 2)
    login_y = (screen_height // 2) - (login_height // 2)
    login_window.geometry(f'{login_width}x{login_height}+{login_x}+{login_y}')

# Function to queue data
def queue_data():
    global queued_df
    filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if filename:
        queued_df = pd.read_csv(filename)
        display_data()

# Function to display data in the treeview
def display_data():
    clear_data()
    if not queued_df.empty:
        treeview["columns"] = list(queued_df.columns)
        for col in queued_df.columns:
            treeview.heading(col, text=col, anchor='center')
            treeview.column(col, anchor="center", width=150)
        for row in queued_df.to_numpy().tolist():
            treeview.insert("", "end", values=row)

# Function to upload queued data to MongoDB
def upload_queued_data():
    global queued_df
    if not queued_df.empty:
        upload_response = messagebox.askyesno("Confirm Upload", "Are you sure you want to upload the queued data?")
        if upload_response:
            data_to_upload = queued_df.to_dict('records')
            db = client['processes_db']
            collection = db['macchinari']
            collection.insert_many(data_to_upload)  # Using insert_many for efficiency
            messagebox.showinfo("Upload Complete", "Data has been successfully uploaded.")
            clear_data()

# Function to clear data in the treeview
def clear_data():
    treeview.delete(*treeview.get_children())
    init_placeholder()

# Function to initialize placeholder in the treeview
def init_placeholder():
    treeview.insert("", "end", values=("Upload a csv file to visualize the data",))

# Function to wipe the database
def wipe_database():
    response = messagebox.askyesno("Confirm Wipe", "Are you sure you want to wipe the database?")
    if response:
        db = client['processes_db']
        collection = db['macchinari']
        collection.delete_many({})  # Deletes all documents in the collection
        clear_data()
        messagebox.showinfo("Success", "The database has been wiped.")

# Function to select database and collection
def select_database_and_collection():
    # Fetch databases and collections
    databases = client.list_database_names()
    
    def on_database_select(*args):
        selected_db = db_var.get()
        collections = client[selected_db].list_collection_names()
        coll_menu['menu'].delete(0, 'end')
        for coll in collections:
            coll_menu['menu'].add_command(label=coll, command=tk._setit(coll_var, coll))
        coll_var.set('')  # Reset collection selection

    # Create popup window
    popup = tk.Toplevel(root)
    popup.title("Select Database and Collection")
    
    tk.Label(popup, text="Select Database:", font=("Proxima Nova", 12)).grid(row=0, column=0, padx=10, pady=10)
    db_var = tk.StringVar(popup)
    db_menu = tk.OptionMenu(popup, db_var, *databases)
    db_menu.config(font=("Proxima Nova", 12))
    db_menu.grid(row=0, column=1, padx=10, pady=10)
    db_var.trace("w", on_database_select)
    
    tk.Label(popup, text="Select Collection:", font=("Proxima Nova", 12)).grid(row=1, column=0, padx=10, pady=10)
    coll_var = tk.StringVar(popup)
    coll_menu = tk.OptionMenu(popup, coll_var, '')
    coll_menu.config(font=("Proxima Nova", 12))
    coll_menu.grid(row=1, column=1, padx=10, pady=10)
    
    def on_confirm():
        selected_db = db_var.get()
        selected_coll = coll_var.get()
        if selected_db and selected_coll:
            popup.destroy()
            export_data(selected_db, selected_coll)
        else:
            messagebox.showerror("Error", "Please select both database and collection.")
    
    tk.Button(popup, text="Confirm", command=on_confirm, font=("Proxima Nova", 12)).grid(row=2, column=0, columnspan=2, pady=10)

# Function to export data to CSV
def export_data(db_name, collection_name):
    db = client[db_name]
    collection = db[collection_name]
    cursor = collection.find({})
    data = list(cursor)
    if data:
        df = pd.DataFrame(data)
        if '_id' in df.columns:
            df.drop('_id', axis=1, inplace=True)
        file_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[("CSV files", "*.csv")])
        if file_path:
            df.to_csv(file_path, index=False)
            messagebox.showinfo("Export Successful", "Data has been successfully exported to CSV.")
    else:
        messagebox.showinfo("No Data", "There is no data to export.")

# GUI Setup
root = tk.Tk()
root.withdraw()  # Hide the main window initially

# Show login window
show_login()

# Main window setup after successful login
root.title("Data Uploader")
root.geometry('1400x800+75+75')


screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x_offset = (screen_width - window_width) // 2
y_offset = (screen_height - window_height) // 2

root.geometry(f'{window_width}x{window_height}+{x_offset}+{y_offset}')

# Load and resize the image

resized_logo = original_logo.resize((floor(original_logo_width/4), floor(original_logo_length/4)), Image.Resampling.LANCZOS)
logo = ImageTk.PhotoImage(resized_logo)
logo_label = tk.Label(root, image=logo)
logo_label.image = logo  # Keep a reference!
logo_label.pack()

# Load custom font
custom_font = ("Proxima Nova", 12)

# Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=20)

queue_btn = tk.Button(button_frame, text="Queue Data", command=queue_data, font=custom_font)
queue_btn.grid(row=0, column=0, padx=10)

clear_btn = tk.Button(button_frame, text="Clear Queued Data", command=clear_data, font=custom_font)  
clear_btn.grid(row=0, column=1, padx=10)  

upload_btn = tk.Button(button_frame, text="Upload Queued Data", bg="green", fg="white", command=upload_queued_data, font=custom_font)
upload_btn.grid(row=0, column=2, padx=10)

wipe_btn = tk.Button(button_frame, text="Wipe Database", bg="red", fg="white", command=wipe_database, font=custom_font)
wipe_btn.grid(row=0, column=3, padx=10) 

export_btn = tk.Button(button_frame, text="Export Data", command=select_database_and_collection, font=custom_font)
export_btn.grid(row=0, column=4, padx=10)

frame = tk.Frame(root)
frame.pack(pady=20, fill='both', expand=True)

# Treeview with size constraints
treeview_frame = tk.Frame(frame)
treeview_frame.pack(fill='both', expand=True)

# Configure treeview and scrollbars within the frame
treeview = ttk.Treeview(treeview_frame, show="headings")
treeview.grid(row=0, column=0, sticky='nsew')

scrollbar_y = ttk.Scrollbar(treeview_frame, orient="vertical", command=treeview.yview)
scrollbar_y.grid(row=0, column=1, sticky='ns')
treeview.config(yscrollcommand=scrollbar_y.set)

scrollbar_x = ttk.Scrollbar(treeview_frame, orient="horizontal", command=treeview.xview)
scrollbar_x.grid(row=1, column=0, sticky='ew')
treeview.config(xscrollcommand=scrollbar_x.set)

# Ensure treeview frame resizes correctly
treeview_frame.grid_rowconfigure(0, weight=1)
treeview_frame.grid_columnconfigure(0, weight=1)

init_placeholder()

root.mainloop()
