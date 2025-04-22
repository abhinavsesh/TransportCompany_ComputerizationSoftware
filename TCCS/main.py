# main.py
import tkinter as tk
import database_manager as db
from gui import LoginScreen

def main():
    # Initialize database (creates connection, tables, default admin)
    db.initialize()

    # Set up the main Tkinter window (it will be hidden initially)
    root = tk.Tk()
    root.withdraw() # Hide the root window

    # Start the login process
    login_window = LoginScreen(root)
    root.mainloop() # Start the Tkinter event loop

if __name__ == "__main__":
    main()