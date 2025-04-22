
# gui.py
import tkinter as tk
from tkinter import ttk # Themed widgets
from tkinter import messagebox, simpledialog, filedialog, scrolledtext
from datetime import datetime, timezone
import database_manager as db
from models import User, Branch, Truck, Consignment, Revenue # Import data models
import analytics # Import analytics functions

# --- Helper Functions ---
def _get_branch_name(branch_id, branches_list):
    """Finds branch name from a list of Branch objects."""
    for b in branches_list:
        if b.branch_id == branch_id:
            return b.name
    return "Unknown"

# --- Login Screen ---
class LoginScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent # Keep track of the root window
        self.title("TCCS - Login")
        self.geometry("450x250")
        self.resizable(False, False)
        # Center the window (relative to parent or screen)
        self.parent.eval(f'tk::PlaceWindow {str(self)} center')

        self.user_id = tk.StringVar()
        self.password = tk.StringVar()

        # Make window modal (optional, prevents interaction with parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close) # Handle closing window

        self._create_widgets()
        self.user_id_entry.focus_set() # Set focus to user ID field

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, text="Transport Company Computerization System",
                               font=("Arial", 16, "bold"), anchor=tk.CENTER)
        title_label.pack(pady=(0, 10))

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=10)

        # User ID
        ttk.Label(input_frame, text="User ID:").grid(row=0, column=0, padx=5, pady=8, sticky=tk.W)
        self.user_id_entry = ttk.Entry(input_frame, textvariable=self.user_id, width=30)
        self.user_id_entry.grid(row=0, column=1, padx=5, pady=8)

        # Password
        ttk.Label(input_frame, text="Password:").grid(row=1, column=0, padx=5, pady=8, sticky=tk.W)
        self.password_entry = ttk.Entry(input_frame, textvariable=self.password, show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=5, pady=8)
        self.password_entry.bind("<Return>", self._perform_login) # Bind Enter key

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        login_button = ttk.Button(button_frame, text="Login", command=self._perform_login, width=12)
        login_button.pack(side=tk.LEFT, padx=10)

        exit_button = ttk.Button(button_frame, text="Exit", command=self._on_close, width=12)
        exit_button.pack(side=tk.LEFT, padx=10)

    def _perform_login(self, event=None): # event=None allows calling without keypress
        user_id = self.user_id.get().strip()
        password = self.password.get() # No strip for password

        if not user_id or not password:
            messagebox.showwarning("Login Error", "Please enter both User ID and Password.", parent=self)
            return

        # Call database manager to authenticate
        user = db.authenticate_user(user_id, password)

        if user:
            self.destroy() # Close login window
            # Open the appropriate dashboard
            if user.is_manager():
                dashboard = ManagerDashboard(self.parent, user)
            else:
                dashboard = EmployeeDashboard(self.parent, user)
            dashboard.deiconify() # Show the main dashboard window
        else:
            messagebox.showerror("Login Failed", "Invalid User ID or Password.", parent=self)
            self.password.set("") # Clear password field
            self.user_id_entry.focus_set()

    def _on_close(self):
        """Handles closing the login window or exiting the app."""
        # If login is closed, exit the application entirely
        self.parent.destroy() # Close the hidden root window


# --- Base Dashboard Class ---
class BaseDashboard(tk.Toplevel):
    def __init__(self, parent, user: User, title_suffix: str):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.title(f"TCCS Dashboard - {title_suffix} ({self.user.name})")
        self.geometry("950x700")
        self.protocol("WM_DELETE_WINDOW", self._prompt_logout) # Handle closing

        # Hide the dashboard initially until login is complete
        self.withdraw()

        # Store branch list for lookups (could be refreshed)
        self.all_branches = db.get_all_branches()

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Notebook (Tabbed Pane)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    def _get_branch_name_local(self, branch_id):
         """Helper to get branch name using the stored list."""
         return _get_branch_name(branch_id, self.all_branches)

    def _prompt_logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to logout?", parent=self):
            print(f"User {self.user.user_id} logging out.")
            self.destroy() # Close this dashboard window
            # Re-show login screen by creating a new instance
            login = LoginScreen(self.parent)
            # Make sure the mainloop continues if root was hidden
            # self.parent.deiconify() # No, keep root hidden

    def _create_profile_tab(self):
        """Creates the Profile & Logout tab."""
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # --- Profile Information ---
        info_frame = ttk.LabelFrame(tab_frame, text="User Profile", padding="15")
        info_frame.pack(pady=10, padx=10, fill=tk.X)

        # Use grid layout for profile details
        info_frame.columnconfigure(1, weight=1) # Allow value column to expand

        ttk.Label(info_frame, text="User ID:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=self.user.user_id).grid(row=0, column=1, sticky=tk.W, pady=3)

        ttk.Label(info_frame, text="Name:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=self.user.name).grid(row=1, column=1, sticky=tk.W, pady=3)

        ttk.Label(info_frame, text="Role:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=self.user.role).grid(row=2, column=1, sticky=tk.W, pady=3)

        ttk.Label(info_frame, text="Branch:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=f"{self.user.branch_id} ({self._get_branch_name_local(self.user.branch_id)})").grid(row=3, column=1, sticky=tk.W, pady=3)

        ttk.Label(info_frame, text="Contact:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=self.user.contact or "N/A").grid(row=4, column=1, sticky=tk.W, pady=3)

        ttk.Label(info_frame, text="Address:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky=tk.W, pady=3)
        ttk.Label(info_frame, text=self.user.address or "N/A").grid(row=5, column=1, sticky=tk.W, pady=3)

        # --- Actions ---
        action_frame = ttk.Frame(tab_frame)
        action_frame.pack(pady=20)

        # Placeholder for change password
        change_pw_button = ttk.Button(action_frame, text="Change Password", state=tk.DISABLED)
        change_pw_button.pack(side=tk.LEFT, padx=10)

        logout_button = ttk.Button(action_frame, text="Logout", command=self._prompt_logout)
        logout_button.pack(side=tk.LEFT, padx=10)

        return tab_frame

    # --- Common Tab Refresh Methods ---
    def _refresh_treeview_data(self, treeview, data_fetch_func, column_map):
        """Generic helper to refresh a ttk.Treeview."""
        # Clear existing items
        for item in treeview.get_children():
            treeview.delete(item)
        # Fetch new data
        try:
            items = data_fetch_func()
            # Populate treeview
            for item_obj in items:
                 # Extract values based on column_map keys (attribute names)
                 values = []
                 for attr in column_map.keys():
                     val = getattr(item_obj, attr, '') # Get attribute, default '' if missing
                     # Format specific types if needed
                     if isinstance(val, float):
                         val = f"{val:.2f}"
                     elif isinstance(val, datetime):
                          # Format datetime (use local time?)
                          local_tz = datetime.now().astimezone().tzinfo
                          val = val.astimezone(local_tz).strftime('%Y-%m-%d %H:%M') if val else '-'
                     elif val is None:
                         val = '-' # Display '-' for None values
                     values.append(val)
                 # Use the first column's value (e.g., ID) as the item ID in Treeview
                 item_id = getattr(item_obj, list(column_map.keys())[0], None)
                 if item_id: # Make sure we have an ID
                      treeview.insert("", tk.END, iid=item_id, values=values)
        except Exception as e:
            messagebox.showerror("Refresh Error", f"Failed to load data: {e}", parent=self)

    def _create_generic_view_dialog(self, title, content):
        """Creates a simple Toplevel window to display text content."""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("500x600")
        dialog.grab_set() # Modal

        text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Monospaced", 10))
        text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED) # Read-only

        close_button = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_button.pack(pady=10)


# --- Employee Dashboard ---
class EmployeeDashboard(BaseDashboard):
    def __init__(self, parent, user: User):
        super().__init__(parent, user, f"{user.role.upper()}")

        # Create tabs specific to Employee/Base
        self.consignment_tab_frame = self._create_consignment_tab()
        self.truck_tab_frame = self._create_truck_tab()

        self.notebook.add(self._create_new_consignment_tab(), text=" New Consignment ")
        self.notebook.add(self.consignment_tab_frame, text=" Consignments ")
        self.notebook.add(self.truck_tab_frame, text=" Trucks ")
        self.notebook.add(self._create_profile_tab(), text=" Profile & Logout ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)


    def _on_tab_change(self, event):
        """Callback when notebook tab changes, can be used for refresh."""
        selected_tab_index = self.notebook.index(self.notebook.select())
        tab_text = self.notebook.tab(selected_tab_index, "text").strip()

        # Refresh specific tabs when they become visible
        if tab_text == "Consignments":
             self._refresh_consignment_tab_data()
        elif tab_text == "Trucks":
             self._refresh_truck_tab_data()
        # Add other refreshes if needed


    # --- New Consignment Tab ---
    def _create_new_consignment_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Use a main frame with scrollbar potential if form gets too long
        canvas = tk.Canvas(tab_frame)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        # --- Form Fields ---
        fields = {} # Dictionary to hold input variables/widgets

        # Layout using grid within scrollable_frame
        form_grid = ttk.Frame(scrollable_frame, padding="10")
        form_grid.pack(expand=True, fill=tk.X)
        col_count = 4 # Number of columns in grid layout

        # Helper to add fields
        def add_field(label_text, row, col, widget_type=ttk.Entry, colspan=1, widget_options=None, var_type=tk.StringVar):
            if widget_options is None: widget_options = {}
            var = var_type()
            fields[label_text] = {'var': var}
            ttk.Label(form_grid, text=label_text + (":*" if label_text.endswith('*') else ":")).grid(row=row, column=col, sticky=tk.W, padx=5, pady=3)
            widget = widget_type(form_grid, textvariable=var, **widget_options) if var_type else widget_type(form_grid, **widget_options)
            widget.grid(row=row, column=col+1, columnspan=colspan, sticky=tk.EW, padx=5, pady=3)
            fields[label_text]['widget'] = widget
            # Configure column weights for horizontal expansion
            form_grid.columnconfigure(col+1, weight=1 if colspan==1 else 0)
            return widget # Return the widget for further configuration

        # Helper to add section headers
        def add_section(title, row):
             sep = ttk.Separator(form_grid, orient=tk.HORIZONTAL)
             sep.grid(row=row, column=0, columnspan=col_count, sticky=tk.EW, pady=(10, 2))
             lbl = ttk.Label(form_grid, text=title, font=("Arial", 12, "bold"))
             lbl.grid(row=row+1, column=0, columnspan=col_count, sticky=tk.W, pady=(0, 5))
             return row + 2 # Return next available row

        # --- Consignment Details ---
        current_row = 0
        current_row = add_section("Consignment Details", current_row)
        add_field("Volume (m³)*", current_row, 0)
        add_field("Weight (kg)*", current_row, 2)
        current_row += 1
        add_field("Type*", current_row, 0)
        # Description (Text Area)
        ttk.Label(form_grid, text="Description:").grid(row=current_row, column=2, sticky=tk.NW, padx=5, pady=3) # Align NorthWest
        desc_text = tk.Text(form_grid, height=3, width=30, wrap=tk.WORD)
        desc_text.grid(row=current_row, column=3, sticky=tk.EW, padx=5, pady=3)
        fields['Description'] = {'widget': desc_text} # Store Text widget directly
        current_row += 1

        # --- Sender Details ---
        current_row = add_section("Sender Details", current_row)
        add_field("Sender Name*", current_row, 0)
        add_field("Sender Address*", current_row, 2)
        current_row += 1
        add_field("Sender Contact*", current_row, 0)
        add_field("Sender ID Ref*", current_row, 2)
        current_row += 1

        # --- Receiver Details ---
        current_row = add_section("Receiver Details", current_row)
        add_field("Receiver Name*", current_row, 0)
        add_field("Receiver Address*", current_row, 2)
        current_row += 1
        add_field("Receiver Contact*", current_row, 0)
        add_field("Receiver ID Ref*", current_row, 2)
        current_row += 1

        # --- Routing and Charges ---
        current_row = add_section("Routing and Charges", current_row)
        # Source Branch (Display only)
        ttk.Label(form_grid, text="Source Branch:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Label(form_grid, text=f"{self.user.branch_id} ({self._get_branch_name_local(self.user.branch_id)})", foreground="blue").grid(row=current_row, column=1, sticky=tk.W, padx=5, pady=3)

        # Destination Branch (Combobox)
        ttk.Label(form_grid, text="Destination Branch*:").grid(row=current_row, column=2, sticky=tk.W, padx=5, pady=3)
        dest_combo = ttk.Combobox(form_grid, state="readonly", values=self.all_branches, width=35) # relies on Branch.__str__
        dest_combo.grid(row=current_row, column=3, sticky=tk.EW, padx=5, pady=3)
        dest_combo.bind("<<ComboboxSelected>>", lambda e: _calculate_charges()) # Recalculate on change
        fields['Destination Branch*'] = {'widget': dest_combo}
        current_row += 1

        # Charges Display & Calculation
        charges_var = tk.StringVar(value="Rs. 0.00")
        fields['Charges'] = {'var': charges_var} # Store for reference
        calc_button = ttk.Button(form_grid, text="Calculate Charges", command=lambda: _calculate_charges())
        calc_button.grid(row=current_row, column=0, padx=5, pady=10)
        ttk.Label(form_grid, text="Estimated Charges:").grid(row=current_row, column=1, sticky=tk.E, padx=5, pady=10)
        charges_label = ttk.Label(form_grid, textvariable=charges_var, font=("Arial", 12, "bold"), foreground="darkblue")
        charges_label.grid(row=current_row, column=2, columnspan=2, sticky=tk.W, padx=5, pady=10)
        current_row += 1

        # Required field note
        ttk.Label(form_grid, text="* Indicates required field", font=("Arial", 9, "italic")).grid(row=current_row, column=0, columnspan=col_count, pady=(5,0))


        # --- Form Actions ---
        action_frame = ttk.Frame(scrollable_frame, padding="10")
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        clear_button = ttk.Button(action_frame, text="Clear Form", command=lambda: _clear_form())
        clear_button.pack(side=tk.RIGHT, padx=5)

        create_button = ttk.Button(action_frame, text="Create Consignment & Print Receipt", command=lambda: _create_consignment())
        create_button.pack(side=tk.RIGHT, padx=5)

        # --- Helper Functions for this Tab ---
        def _validate_inputs():
            """Checks if required fields are filled."""
            required_labels = [k for k in fields if k.endswith('*')]
            missing = []
            for label in required_labels:
                widget = fields[label]['widget']
                value = ""
                if isinstance(widget, ttk.Entry) or isinstance(widget, ttk.Combobox):
                     value = fields[label]['var'].get().strip()
                elif isinstance(widget, tk.Text):
                     value = widget.get("1.0", tk.END).strip()

                if not value:
                     missing.append(label.replace('*',''))

            if missing:
                messagebox.showwarning("Input Error", "Please fill in all required fields:\n- " + "\n- ".join(missing), parent=tab_frame)
                return False

            # Specific validation (e.g., numbers)
            try:
                 float(fields['Volume (m³)*']['var'].get())
                 float(fields['Weight (kg)*']['var'].get())
            except ValueError:
                 messagebox.showwarning("Input Error", "Volume and Weight must be valid numbers.", parent=tab_frame)
                 return False
            return True

        def _clear_form():
            """Clears all input fields."""
            for label, data in fields.items():
                 widget = data['widget']
                 if isinstance(widget, ttk.Entry):
                     data['var'].set("")
                 elif isinstance(widget, ttk.Combobox):
                     widget.set('') # Clear selection
                 elif isinstance(widget, tk.Text):
                     widget.delete("1.0", tk.END)
            fields['Charges']['var'].set("Rs. 0.00") # Reset charges label

        def _calculate_charges():
            """Calculates and updates the charges label."""
            try:
                volume = float(fields['Volume (m³)*']['var'].get())
                weight = float(fields['Weight (kg)*']['var'].get())
                selected_branch_str = fields['Destination Branch*']['widget'].get()
                if not selected_branch_str:
                    # messagebox.showwarning("Input Error", "Please select a destination branch.", parent=tab_frame)
                    return # Don't show error, just don't calculate yet

                # Find the selected Branch object
                selected_branch = next((b for b in self.all_branches if str(b) == selected_branch_str), None)
                if not selected_branch:
                     # This shouldn't happen if combobox values are Branch objects
                     print("Error: Could not find selected branch object.")
                     return

                dest_branch_id = selected_branch.branch_id
                charges = Consignment.calculate_charges(volume, weight, self.user.branch_id, dest_branch_id)
                fields['Charges']['var'].set(f"Rs. {charges:.2f}")
                return charges
            except ValueError:
                # Don't show error on every keystroke if numbers invalid
                # messagebox.showerror("Input Error", "Invalid volume or weight.", parent=tab_frame)
                fields['Charges']['var'].set("Rs. 0.00")
                return None
            except Exception as e:
                 messagebox.showerror("Error", f"Error calculating charges: {e}", parent=tab_frame)
                 fields['Charges']['var'].set("Rs. 0.00")
                 return None

        def _create_consignment():
            """Handles the consignment creation process."""
            if not _validate_inputs():
                return

            # Recalculate/confirm charges
            charges = _calculate_charges()
            if charges is None: # Calculation failed (e.g., invalid volume/weight)
                if not messagebox.askokcancel("Input Error", "Volume or Weight seems invalid. Cannot calculate charges.\nFix the values and click 'Calculate Charges' first, or proceed without calculated charges?", parent=tab_frame):
                     return # User cancelled
                charges = 0.0 # Proceed with zero charges if user confirms

            # Get values from fields
            volume = float(fields['Volume (m³)*']['var'].get())
            weight = float(fields['Weight (kg)*']['var'].get())
            ctype = fields['Type*']['var'].get()
            desc = fields['Description']['widget'].get("1.0", tk.END).strip()
            sender_name = fields['Sender Name*']['var'].get()
            sender_addr = fields['Sender Address*']['var'].get()
            sender_contact = fields['Sender Contact*']['var'].get()
            sender_id = fields['Sender ID Ref*']['var'].get()
            rec_name = fields['Receiver Name*']['var'].get()
            rec_addr = fields['Receiver Address*']['var'].get()
            rec_contact = fields['Receiver Contact*']['var'].get()
            rec_id = fields['Receiver ID Ref*']['var'].get()

            selected_branch_str = fields['Destination Branch*']['widget'].get()
            selected_branch = next((b for b in self.all_branches if str(b) == selected_branch_str), None)
            dest_branch_id = selected_branch.branch_id

            # Generate ID
            consignment_id = db.generate_next_id('CON', 'consignments', 'consignment_id')
            now_utc = datetime.now(timezone.utc)

            new_consignment = Consignment(
                 consignment_id=consignment_id, volume=volume, weight=weight, type=ctype, description=desc,
                 sender_name=sender_name, sender_address=sender_addr, sender_contact=sender_contact, sender_id=sender_id,
                 receiver_name=rec_name, receiver_address=rec_addr, receiver_contact=rec_contact, receiver_id=rec_id,
                 source_branch=self.user.branch_id, destination_branch=dest_branch_id, truck_id=None,
                 status='PENDING', charges=charges, created_at=now_utc, delivered_at=None
            )

            # Save to database
            success, saved_id = db.add_consignment(new_consignment)

            if success and saved_id:
                 messagebox.showinfo("Success", f"Consignment '{saved_id}' created successfully.", parent=tab_frame)

                 # Generate and show receipt
                 receipt_text = new_consignment.generate_receipt() # Use the created object
                 self._create_generic_view_dialog(f"Receipt: {saved_id}", receipt_text)

                 # Offer to save receipt
                 try:
                     file_path = filedialog.asksaveasfilename(
                         defaultextension=".txt",
                         initialfile=f"receipt_{saved_id}.txt",
                         title="Save Receipt As",
                         parent=tab_frame
                     )
                     if file_path:
                         with open(file_path, 'w', encoding='utf-8') as f:
                             f.write(receipt_text)
                         print(f"Receipt saved to {file_path}")
                 except Exception as e:
                     messagebox.showwarning("File Save Error", f"Could not save receipt:\n{e}", parent=tab_frame)

                 _clear_form()
                 # Optionally switch to and refresh consignments tab
                 # Find the index of the Consignments tab
                 try:
                     cons_tab_index = self.notebook.index(self.consignment_tab_frame)
                     self.notebook.select(cons_tab_index) # Switch to the tab
                     # Refresh will happen via _on_tab_change binding
                 except tk.TclError:
                      print("Consignments tab frame not found.") # Should exist
                 # self._refresh_consignment_tab_data() # Explicit refresh if needed

            else:
                 # Error message shown by db.add_consignment
                 pass # Maybe log here

        return tab_frame

    # --- Consignments Tab ---
    def _create_consignment_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Table (Treeview)
        columns = {
            'consignment_id': ("ID", 60),
            'status': ("Status", 80),
            'sender_name': ("Sender", 100),
            'receiver_name': ("Receiver", 100),
            'source_branch': ("Source", 70),
            'destination_branch': ("Destination", 80),
            'truck_id': ("Truck", 60),
            'charges': ("Charges (Rs)", 90),
            'created_at': ("Created", 120),
            'delivered_at': ("Delivered", 120)
        }
        column_ids = list(columns.keys())
        display_columns = [cid for cid in column_ids if cid != 'consignment_id'] # Hide ID column visually if needed

        tree = ttk.Treeview(tab_frame, columns=column_ids, show="headings", selectmode="browse") # browse=single selection

        for col_id, (text, width) in columns.items():
            tree.heading(col_id, text=text, anchor=tk.W)
            tree.column(col_id, width=width, anchor=tk.W, stretch=tk.NO) # Prevent stretching initially

        # Scrollbars
        vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(expand=True, fill=tk.BOTH)

        self.consignment_tree = tree # Store reference

        # Action Buttons
        action_frame = ttk.Frame(tab_frame, padding=(0, 5, 0, 0))
        action_frame.pack(fill=tk.X)

        ttk.Button(action_frame, text="View Details", command=self._view_consignment_details).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Update Status", command=self._update_consignment_status).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Allocate Pending to Truck", command=self._show_allocate_truck_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Refresh List", command=self._refresh_consignment_tab_data).pack(side=tk.LEFT, padx=3)

        return tab_frame

    def _refresh_consignment_tab_data(self):
        """Refreshes the data in the consignment treeview."""
        if hasattr(self, 'consignment_tree'):
            # Define mapping from model attribute to column data tuple (text, width)
            columns_map = {
                'consignment_id': ("ID", 60),
                'status': ("Status", 80),
                'sender_name': ("Sender", 100),
                'receiver_name': ("Receiver", 100),
                'source_branch': ("Source", 70),
                'destination_branch': ("Destination", 80),
                'truck_id': ("Truck", 60),
                'charges': ("Charges (Rs)", 90),
                'created_at': ("Created", 120),
                'delivered_at': ("Delivered", 120)
            }
            self._refresh_treeview_data(
                self.consignment_tree,
                lambda: db.get_consignments_by_branch(self.user.branch_id),
                columns_map
            )

    def _get_selected_consignment_id(self):
        """Gets the ID of the selected item in the consignment tree."""
        selected = self.consignment_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a consignment from the table first.", parent=self)
            return None
        # The item ID (iid) is the consignment_id we inserted
        return selected[0]

    def _view_consignment_details(self):
        """Shows the receipt for the selected consignment."""
        consignment_id = self._get_selected_consignment_id()
        if not consignment_id: return

        consignment = db.get_consignment_by_id(consignment_id)
        if consignment:
            receipt_text = consignment.generate_receipt()
            self._create_generic_view_dialog(f"Details: {consignment_id}", receipt_text)
        else:
            messagebox.showerror("Error", f"Could not retrieve details for consignment {consignment_id}.", parent=self)

    def _update_consignment_status(self):
        """Opens a dialog to update the status of the selected consignment."""
        consignment_id = self._get_selected_consignment_id()
        if not consignment_id: return

        # Get current status directly from the treeview item data
        item_data = self.consignment_tree.item(consignment_id, 'values')
        if not item_data or len(item_data) < 2: # Need at least ID and Status columns
             messagebox.showerror("Error", "Could not get current status from table.", parent=self)
             return
        current_status = item_data[1] # Assuming status is the second column value
        destination_branch = item_data[5] # Assuming destination is the 6th column

        status_options = []
        if current_status == 'PENDING':
            status_options = ['PENDING', 'IN_TRANSIT', 'CANCELLED']
        elif current_status == 'IN_TRANSIT':
            # Can mark delivered only if at the destination branch
            if self.user.branch_id == destination_branch:
                 status_options = ['IN_TRANSIT', 'DELIVERED', 'CANCELLED']
            else:
                 status_options = ['IN_TRANSIT', 'CANCELLED'] # Cannot mark delivered elsewhere
        elif current_status in ['DELIVERED', 'CANCELLED']:
            messagebox.showinfo("Status Update", f"Consignment is already {current_status}. No further changes possible.", parent=self)
            return
        else: # Fallback (shouldn't happen with ENUM)
            status_options = ['PENDING', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED']

        # Use SimpleDialog for status selection
        new_status = simpledialog.askstring(
            "Update Consignment Status",
            f"Select new status for Consignment ID: {consignment_id}\n"
            f"(Current: {current_status})\n"
            f"Options: {', '.join(status_options)}",
            parent=self,
            initialvalue=current_status
        )

        if new_status and new_status in status_options and new_status != current_status:
            if messagebox.askyesno("Confirm Status Change", f"Change status from '{current_status}' to '{new_status}'?", parent=self):
                 success = db.update_consignment_status(consignment_id, new_status)
                 if success:
                     messagebox.showinfo("Success", f"Status updated successfully to {new_status}.", parent=self)
                     self._refresh_consignment_tab_data()
                     self._refresh_truck_tab_data() # Truck status might change on delivery
                 else:
                     # Error message shown by db function
                     pass
        elif new_status and new_status not in status_options:
             messagebox.showwarning("Invalid Status", f"'{new_status}' is not a valid next status option.", parent=self)


    def _show_allocate_truck_dialog(self):
        """Shows the dialog for allocating a truck to pending consignments."""
        AllocateTruckDialog(self, self.user, self.all_branches)
        # Refresh lists after dialog closes (whether successful or not)
        self._refresh_consignment_tab_data()
        self._refresh_truck_tab_data()

    # --- Trucks Tab ---
    def _create_truck_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Table (Treeview)
        columns = {
            'truck_id': ("ID", 60),
            'registration_no': ("Reg. No", 90),
            'status': ("Status", 90),
            'capacity': ("Capacity (m³)", 90),
            'driver_name': ("Driver", 110),
            'driver_contact': ("Driver Contact", 110),
            'source_branch': ("Current Branch", 100), # Renamed for clarity
            'destination_branch': ("Destination", 100),
            'idle_since': ("Idle Since", 130)
        }
        column_ids = list(columns.keys())

        tree = ttk.Treeview(tab_frame, columns=column_ids, show="headings", selectmode="browse")

        for col_id, (text, width) in columns.items():
            tree.heading(col_id, text=text, anchor=tk.W)
            tree.column(col_id, width=width, anchor=tk.W, stretch=tk.NO)

        vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(expand=True, fill=tk.BOTH)

        self.truck_tree = tree # Store reference

        # Action Buttons
        action_frame = ttk.Frame(tab_frame, padding=(0, 5, 0, 0))
        action_frame.pack(fill=tk.X)

        ttk.Button(action_frame, text="Add New Truck", command=self._show_add_truck_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Update Status", command=self._show_update_truck_status_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Refresh List", command=self._refresh_truck_tab_data).pack(side=tk.LEFT, padx=3)

        return tab_frame

    def _refresh_truck_tab_data(self):
        """Refreshes the data in the truck treeview."""
        if hasattr(self, 'truck_tree'):
            columns_map = {
                'truck_id': ("ID", 60),
                'registration_no': ("Reg. No", 90),
                'status': ("Status", 90),
                'capacity': ("Capacity (m³)", 90),
                'driver_name': ("Driver", 110),
                'driver_contact': ("Driver Contact", 110),
                'source_branch': ("Current Branch", 100),
                'destination_branch': ("Destination", 100),
                'idle_since': ("Idle Since", 130)
            }
            self._refresh_treeview_data(
                self.truck_tree,
                db.get_all_trucks, # Fetch all trucks
                columns_map
            )

    def _get_selected_truck_info(self):
        """Gets ID, status, and source branch of the selected truck."""
        selected = self.truck_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a truck from the table first.", parent=self)
            return None, None, None
        item_id = selected[0]
        item_data = self.truck_tree.item(item_id, 'values')
        if not item_data or len(item_data) < 7: # Need ID, Status, SourceBranch
            messagebox.showerror("Error", "Could not get truck data from table.", parent=self)
            return None, None, None

        # Assuming columns: ID[0], RegNo[1], Status[2], Cap[3], DrName[4], DrCon[5], SourceBr[6]...
        status = item_data[2]
        source_branch = item_data[6]
        return item_id, status, source_branch

    def _show_add_truck_dialog(self):
        """Shows the dialog for adding a new truck."""
        AddEditTruckDialog(self, self.user, self.all_branches, None) # None indicates Add mode
        self._refresh_truck_tab_data() # Refresh after dialog closes

    def _show_update_truck_status_dialog(self):
        """Shows the dialog for updating the selected truck's status."""
        truck_id, current_status, current_source_branch = self._get_selected_truck_info()
        if not truck_id:
            return

        UpdateTruckStatusDialog(self, self.all_branches, truck_id, current_status, current_source_branch)
        self._refresh_truck_tab_data() # Refresh after dialog closes


# --- Manager Dashboard ---
class ManagerDashboard(EmployeeDashboard): # Inherit from Employee
    def __init__(self, parent, user: User):
        # Call parent constructor first
        super().__init__(parent, user)
        # Adjust title set by parent if needed, or set directly
        self.title(f"TCCS Dashboard - MANAGER ({self.user.name})")


        # Create Manager-specific tabs
        self.user_mgmt_tab_frame = self._create_user_management_tab()
        self.branch_mgmt_tab_frame = self._create_branch_management_tab()
        self.revenue_tab_frame = self._create_revenue_report_tab()
        self.analytics_tab_frame = self._create_analytics_tab()

        # Insert manager tabs at the beginning
        self.notebook.insert(0, self.user_mgmt_tab_frame, text=" User Management ")
        self.notebook.insert(1, self.branch_mgmt_tab_frame, text=" Branch Management ")
        self.notebook.insert(2, self.revenue_tab_frame, text=" Revenue Report ")
        self.notebook.insert(3, self.analytics_tab_frame, text=" Analytics ")

        # Re-bind tab change to include refreshing new tabs if necessary
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change_manager)


    def _on_tab_change_manager(self, event):
        """Manager version of tab change handler."""
        super()._on_tab_change(event) # Call base handler first

        selected_tab_index = self.notebook.index(self.notebook.select())
        tab_text = self.notebook.tab(selected_tab_index, "text").strip()

        # Refresh manager-specific tabs
        if tab_text == "User Management":
             self._refresh_user_management_data()
        elif tab_text == "Branch Management":
             self._refresh_branch_management_data()
        elif tab_text == "Revenue Report":
             self._refresh_revenue_report_data()
        elif tab_text == "Analytics":
             self._refresh_analytics_data()


    # --- User Management Tab ---
    def _create_user_management_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Treeview setup
        columns = {
            'user_id': ("User ID", 100), 'name': ("Name", 150), 'role': ("Role", 80),
            'branch_id': ("Branch ID", 80), 'contact': ("Contact", 120), 'address': ("Address", 200)
        }
        tree = ttk.Treeview(tab_frame, columns=list(columns.keys()), show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for col_id, (text, width) in columns.items():
            tree.heading(col_id, text=text, anchor=tk.W)
            tree.column(col_id, width=width, anchor=tk.W, stretch=tk.NO)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(expand=True, fill=tk.BOTH)
        self.user_tree = tree

        # Action Buttons
        action_frame = ttk.Frame(tab_frame, padding=(0, 5, 0, 0))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Add New User", command=self._show_add_user_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Edit User", state=tk.DISABLED).pack(side=tk.LEFT, padx=3) # TODO
        ttk.Button(action_frame, text="Delete User", state=tk.DISABLED).pack(side=tk.LEFT, padx=3) # TODO (with caution)
        ttk.Button(action_frame, text="Refresh List", command=self._refresh_user_management_data).pack(side=tk.LEFT, padx=3)

        return tab_frame

    def _refresh_user_management_data(self):
         if hasattr(self, 'user_tree'):
            columns_map = {
                'user_id': ("User ID", 100), 'name': ("Name", 150), 'role': ("Role", 80),
                'branch_id': ("Branch ID", 80), 'contact': ("Contact", 120), 'address': ("Address", 200)
            }
            self._refresh_treeview_data(self.user_tree, db.get_all_users, columns_map)

    def _show_add_user_dialog(self):
         AddEditUserDialog(self, self.all_branches, None) # Add mode
         self._refresh_user_management_data()


    # --- Branch Management Tab ---
    def _create_branch_management_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Treeview setup
        columns = {
            'branch_id': ("Branch ID", 80), 'name': ("Name", 150), 'location': ("Location", 150),
            'contact': ("Contact", 120), 'address': ("Address", 250)
        }
        tree = ttk.Treeview(tab_frame, columns=list(columns.keys()), show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for col_id, (text, width) in columns.items():
            tree.heading(col_id, text=text, anchor=tk.W)
            tree.column(col_id, width=width, anchor=tk.W, stretch=tk.NO)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(expand=True, fill=tk.BOTH)
        self.branch_tree = tree

        # Action Buttons
        action_frame = ttk.Frame(tab_frame, padding=(0, 5, 0, 0))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Add New Branch", command=self._show_add_branch_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Edit Branch", state=tk.DISABLED).pack(side=tk.LEFT, padx=3) # TODO
        ttk.Button(action_frame, text="Delete Branch", state=tk.DISABLED).pack(side=tk.LEFT, padx=3) # TODO (very carefully due to FKs)
        ttk.Button(action_frame, text="Refresh List", command=self._refresh_branch_management_data).pack(side=tk.LEFT, padx=3)

        return tab_frame

    def _refresh_branch_management_data(self):
        if hasattr(self, 'branch_tree'):
            columns_map = {
                'branch_id': ("Branch ID", 80), 'name': ("Name", 150), 'location': ("Location", 150),
                'contact': ("Contact", 120), 'address': ("Address", 250)
            }
            # Refresh local cache of branches as well
            self.all_branches = db.get_all_branches()
            self._refresh_treeview_data(self.branch_tree, lambda: self.all_branches, columns_map)


    def _show_add_branch_dialog(self):
        AddEditBranchDialog(self, None) # Add mode
        self._refresh_branch_management_data()


    # --- Revenue Report Tab ---
    def _create_revenue_report_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Text Area for Report
        report_text = scrolledtext.ScrolledText(tab_frame, wrap=tk.WORD, font=("Monospaced", 10), state=tk.DISABLED)
        report_text.pack(expand=True, fill=tk.BOTH, pady=(0, 5))
        self.revenue_report_area = report_text

        # Action Buttons
        action_frame = ttk.Frame(tab_frame)
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Refresh Report", command=self._refresh_revenue_report_data).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Export Report", command=self._export_revenue_report).pack(side=tk.LEFT, padx=3)

        return tab_frame

    def _refresh_revenue_report_data(self):
        if hasattr(self, 'revenue_report_area'):
             report_content = analytics.generate_revenue_report()
             self.revenue_report_area.config(state=tk.NORMAL) # Enable writing
             self.revenue_report_area.delete('1.0', tk.END)
             self.revenue_report_area.insert('1.0', report_content)
             self.revenue_report_area.config(state=tk.DISABLED) # Disable writing

    def _export_revenue_report(self):
         if not hasattr(self, 'revenue_report_area'): return
         report_content = self.revenue_report_area.get('1.0', tk.END).strip()
         if not report_content:
             messagebox.showwarning("Export Error", "Report content is empty.", parent=self)
             return

         try:
             file_path = filedialog.asksaveasfilename(
                 defaultextension=".txt",
                 initialfile=f"TCCS_Revenue_Report_{datetime.now().strftime('%Y%m%d')}.txt",
                 title="Save Revenue Report As",
                 parent=self
             )
             if file_path:
                 with open(file_path, 'w', encoding='utf-8') as f:
                     f.write(report_content)
                 messagebox.showinfo("Export Successful", f"Report saved to:\n{file_path}", parent=self)
         except Exception as e:
             messagebox.showerror("Export Error", f"Could not save report:\n{e}", parent=self)


    # --- Analytics Tab ---
    def _create_analytics_tab(self):
        tab_frame = ttk.Frame(self.notebook, padding="10")
        tab_frame.pack(expand=True, fill=tk.BOTH)

        # Text Area for Summary
        summary_text = scrolledtext.ScrolledText(tab_frame, wrap=tk.WORD, font=("Monospaced", 10), state=tk.DISABLED)
        summary_text.pack(expand=True, fill=tk.BOTH, pady=(0, 5))
        self.analytics_summary_area = summary_text

        # Action Buttons
        action_frame = ttk.Frame(tab_frame)
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Refresh Analytics", command=self._refresh_analytics_data).pack(side=tk.LEFT, padx=3)
        # Export could be added similarly to revenue

        return tab_frame

    def _refresh_analytics_data(self):
        if hasattr(self, 'analytics_summary_area'):
             summary_content = analytics.generate_analytics_summary()
             self.analytics_summary_area.config(state=tk.NORMAL)
             self.analytics_summary_area.delete('1.0', tk.END)
             self.analytics_summary_area.insert('1.0', summary_content)
             self.analytics_summary_area.config(state=tk.DISABLED)


# --- Dialog Windows ---

class AllocateTruckDialog(tk.Toplevel):
    def __init__(self, parent, user, branches):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.branches = [b for b in branches if b.branch_id != user.branch_id] # Exclude source

        self.title("Allocate Truck")
        self.geometry("550x300")
        self.grab_set() # Modal

        self.selected_dest_branch = tk.StringVar()
        self.selected_truck = tk.StringVar()
        self.pending_info_var = tk.StringVar(value="Select destination to see pending volume.")
        self.available_trucks = [] # List of Truck objects

        self._create_widgets()
        # Initial population? Could trigger the callback if needed.

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        # Source Branch
        ttk.Label(main_frame, text="Source Branch:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(main_frame, text=f"{self.user.branch_id} ({_get_branch_name(self.user.branch_id, self.branches + [Branch(self.user.branch_id, 'Current', '', '', '')])})", foreground="blue").grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # Destination Branch
        ttk.Label(main_frame, text="Destination Branch:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.dest_combo = ttk.Combobox(main_frame, textvariable=self.selected_dest_branch,
                                       values=self.branches, state="readonly", width=40)
        self.dest_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.dest_combo.bind("<<ComboboxSelected>>", self._on_destination_selected)

        # Pending Info
        ttk.Label(main_frame, textvariable=self.pending_info_var, font=("Arial", 9, "italic")).grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)

        # Available Truck
        ttk.Label(main_frame, text="Available Truck:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.truck_combo = ttk.Combobox(main_frame, textvariable=self.selected_truck, state=tk.DISABLED, width=40)
        self.truck_combo.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=15)
        ttk.Button(button_frame, text="Allocate Selected Truck", command=self._allocate).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=10)


    def _on_destination_selected(self, event=None):
        dest_str = self.selected_dest_branch.get()
        if not dest_str: return

        selected_branch = next((b for b in self.branches if str(b) == dest_str), None)
        if not selected_branch: return
        dest_branch_id = selected_branch.branch_id

        # Fetch pending volume
        pending_volume = db.get_total_pending_volume(self.user.branch_id, dest_branch_id)
        self.pending_info_var.set(f"Total Pending Volume for {dest_branch_id}: {pending_volume:.2f} m³")

        # Fetch and populate available trucks
        self.available_trucks = db.get_available_trucks_by_branch(self.user.branch_id)
        self.truck_combo['values'] = [str(t) for t in self.available_trucks] # Display truck __str__

        if not self.available_trucks:
            self.truck_combo.set('')
            self.truck_combo.config(state=tk.DISABLED)
            self.pending_info_var.set(self.pending_info_var.get() + " (No trucks available at source)")
        else:
            self.truck_combo.config(state="readonly")
            self.truck_combo.current(0) # Select first truck by default

    def _allocate(self):
        dest_str = self.selected_dest_branch.get()
        truck_str = self.selected_truck.get()

        if not dest_str or not truck_str:
            messagebox.showwarning("Input Error", "Please select both destination and truck.", parent=self)
            return

        selected_dest = next((b for b in self.branches if str(b) == dest_str), None)
        selected_truck_obj = next((t for t in self.available_trucks if str(t) == truck_str), None)

        if not selected_dest or not selected_truck_obj:
            messagebox.showerror("Error", "Invalid selection.", parent=self)
            return

        dest_branch_id = selected_dest.branch_id
        truck_id = selected_truck_obj.truck_id

        pending_volume = db.get_total_pending_volume(self.user.branch_id, dest_branch_id)
        if pending_volume <= 0:
             messagebox.showinfo("Allocation Info", f"No pending consignments found for destination {dest_branch_id}.", parent=self)
             return

        confirm_msg = f"Allocate truck {truck_id} to all PENDING consignments for destination {dest_branch_id}?"
        # Optional: Add capacity warning
        if selected_truck_obj.capacity < pending_volume:
             confirm_msg += f"\n\nWarning: Truck capacity ({selected_truck_obj.capacity:.2f} m³) is less than pending volume ({pending_volume:.2f} m³)."

        if messagebox.askyesno("Confirm Allocation", confirm_msg, parent=self):
             success = db.allocate_truck_to_consignments(self.user.branch_id, dest_branch_id, truck_id)
             if success:
                 messagebox.showinfo("Success", f"Truck {truck_id} allocated.\nConsignments set to IN_TRANSIT.", parent=self)
                 self.destroy() # Close dialog on success
             else:
                 # Error message likely shown by db function
                 pass

# --- Add/Edit Truck Dialog ---
class AddEditTruckDialog(tk.Toplevel):
    def __init__(self, parent, user, branches, truck_to_edit: Truck = None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.branches = branches
        self.editing_truck = truck_to_edit

        mode = "Edit" if self.editing_truck else "Add"
        self.title(f"{mode} Truck")
        self.geometry("450x350")
        self.grab_set()

        # Variables
        self.reg_no = tk.StringVar()
        self.capacity = tk.DoubleVar()
        self.driver_name = tk.StringVar()
        self.driver_contact = tk.StringVar()
        self.initial_branch = tk.StringVar() # Stores the __str__ representation

        if self.editing_truck:
             # Pre-fill fields for editing (status/location handled separately)
             self.reg_no.set(self.editing_truck.registration_no)
             self.capacity.set(self.editing_truck.capacity)
             self.driver_name.set(self.editing_truck.driver_name or "")
             self.driver_contact.set(self.editing_truck.driver_contact or "")
             # Find the branch object to set the combo value
             initial_branch_obj = next((b for b in branches if b.branch_id == self.editing_truck.source_branch), None)
             if initial_branch_obj:
                  self.initial_branch.set(str(initial_branch_obj))
        else:
             # Default initial branch to user's branch for Add mode
             user_branch_obj = next((b for b in branches if b.branch_id == user.branch_id), None)
             if user_branch_obj:
                  self.initial_branch.set(str(user_branch_obj))


        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Registration No:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.reg_no).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Capacity (m³):*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.capacity).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Driver Name:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.driver_name).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Driver Contact:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.driver_contact).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        # Initial Branch (relevant for adding, source branch if editing)
        branch_label_text = "Initial Branch:*" if not self.editing_truck else "Source Branch:"
        ttk.Label(main_frame, text=branch_label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        branch_combo = ttk.Combobox(main_frame, textvariable=self.initial_branch, values=self.branches, state="readonly")
        branch_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        # Disable changing source branch when editing? Maybe allowed.
        # if self.editing_truck: branch_combo.config(state=tk.DISABLED)
        row += 1

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        save_text = "Save Truck" # if not self.editing_truck else "Update Truck" # TODO: Add update logic
        ttk.Button(button_frame, text=save_text, command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=10)


    def _save(self):
        reg_no = self.reg_no.get().strip()
        try:
            capacity = self.capacity.get()
        except tk.TclError:
            messagebox.showerror("Input Error", "Capacity must be a valid number.", parent=self)
            return
        driver_name = self.driver_name.get().strip()
        driver_contact = self.driver_contact.get().strip()
        branch_str = self.initial_branch.get()

        if not reg_no or capacity <= 0 or not branch_str:
            messagebox.showwarning("Input Error", "Registration No, positive Capacity, and Branch are required.", parent=self)
            return

        selected_branch = next((b for b in self.branches if str(b) == branch_str), None)
        if not selected_branch:
             messagebox.showerror("Error", "Invalid branch selected.", parent=self)
             return

        if self.editing_truck:
            # --- Update Logic (TODO) ---
            messagebox.showinfo("Not Implemented", "Update truck functionality is not yet implemented.", parent=self)
            # 1. Create updated Truck object
            # 2. Call db.update_truck(...) function (needs to be created)
            # 3. Handle success/failure
            pass
        else:
            # --- Add Logic ---
            truck_id = db.generate_next_id('TR', 'trucks', 'truck_id')
            now = datetime.now(timezone.utc) # Use aware datetime

            new_truck = Truck(
                truck_id=truck_id,
                registration_no=reg_no,
                capacity=capacity,
                driver_name=driver_name or None,
                driver_contact=driver_contact or None,
                status='AVAILABLE', # New trucks are available
                source_branch=selected_branch.branch_id,
                current_location=selected_branch.location, # Set initial location
                destination_branch=None,
                idle_since=now
            )

            success = db.add_truck(new_truck)
            if success:
                 messagebox.showinfo("Success", f"Truck {truck_id} added successfully.", parent=self)
                 self.destroy()
            # else: Error shown by db function


# --- Update Truck Status Dialog ---
class UpdateTruckStatusDialog(tk.Toplevel):
     def __init__(self, parent, branches, truck_id, current_status, current_source_branch):
        super().__init__(parent)
        self.parent = parent
        self.branches = branches
        self.truck_id = truck_id
        self.current_status = current_status
        self.current_source_branch = current_source_branch

        self.title(f"Update Status: {truck_id}")
        self.geometry("400x250")
        self.grab_set()

        self.new_status = tk.StringVar(value=current_status)
        self.selected_branch = tk.StringVar() # Stores __str__

        # Find current branch object for initial selection
        current_branch_obj = next((b for b in branches if b.branch_id == current_source_branch), None)
        if current_branch_obj:
             self.selected_branch.set(str(current_branch_obj))


        self._create_widgets()
        self._update_branch_label() # Initial label setup


     def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        row=0
        ttk.Label(main_frame, text="Current Status:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(main_frame, text=self.current_status).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        ttk.Label(main_frame, text="New Status:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        status_options = ["AVAILABLE", "IN_TRANSIT", "MAINTENANCE"]
        self.status_combo = ttk.Combobox(main_frame, textvariable=self.new_status, values=status_options, state="readonly")
        self.status_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.status_combo.bind("<<ComboboxSelected>>", self._update_branch_label)
        row += 1

        self.branch_label = ttk.Label(main_frame, text="Branch:*") # Text updated dynamically
        self.branch_label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.branch_combo = ttk.Combobox(main_frame, textvariable=self.selected_branch, values=self.branches, state="readonly")
        self.branch_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        row += 1

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="Update Status", command=self._update_status).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=10)

     def _update_branch_label(self, event=None):
         """Updates the branch label based on the selected status."""
         status = self.new_status.get()
         if status == "IN_TRANSIT":
             self.branch_label.config(text="Destination Branch:*")
             self.branch_combo.config(state="readonly")
         elif status in ["AVAILABLE", "MAINTENANCE"]:
             self.branch_label.config(text="Current Branch:*")
             self.branch_combo.config(state="readonly")
         else: # Should not happen with readonly combo
             self.branch_label.config(text="Branch:")
             self.branch_combo.config(state=tk.DISABLED)

     def _update_status(self):
         new_status = self.new_status.get()
         branch_str = self.selected_branch.get()

         if not branch_str:
             messagebox.showwarning("Input Error", "Please select a branch.", parent=self)
             return

         if new_status == self.current_status:
             messagebox.showinfo("No Change", "New status is the same as the current status.", parent=self)
             return

         selected_branch_obj = next((b for b in self.branches if str(b) == branch_str), None)
         if not selected_branch_obj:
             messagebox.showerror("Error", "Invalid branch selected.", parent=self)
             return

         new_destination_branch = None
         new_source_branch = self.current_source_branch # Default

         if new_status == 'IN_TRANSIT':
             new_destination_branch = selected_branch_obj.branch_id
             # Source remains where it was when it departed
             if new_destination_branch == self.current_source_branch:
                  messagebox.showwarning("Input Error", "Destination cannot be the same as the current source branch for IN_TRANSIT.", parent=self)
                  return
         elif new_status in ['AVAILABLE', 'MAINTENANCE']:
             new_destination_branch = None # No destination
             new_source_branch = selected_branch_obj.branch_id # Truck is now based here

         confirm_msg = (
            f"Confirm Update for Truck ID: {self.truck_id}\n"
            f"New Status: {new_status}\n"
            f"{self.branch_label.cget('text').replace(':*','').strip()}: {selected_branch_obj.branch_id}\n\n"
            f"Proceed?"
         )

         if messagebox.askyesno("Confirm Truck Status Update", confirm_msg, parent=self):
             success = db.update_truck_status(self.truck_id, new_status, new_destination_branch, new_source_branch)
             if success:
                 messagebox.showinfo("Success", "Truck status updated successfully.", parent=self)
                 self.destroy()
             # else: Error shown by db function


# --- Add/Edit User Dialog ---
class AddEditUserDialog(tk.Toplevel):
    def __init__(self, parent, branches, user_to_edit: User = None):
        super().__init__(parent)
        self.parent = parent
        self.branches = branches
        self.editing_user = user_to_edit

        mode = "Edit" if self.editing_user else "Add"
        self.title(f"{mode} User")
        self.geometry("450x400")
        self.grab_set()

        # Variables
        self.user_id = tk.StringVar()
        self.password = tk.StringVar()
        self.name = tk.StringVar()
        self.role = tk.StringVar(value="EMPLOYEE") # Default role
        self.branch = tk.StringVar()
        self.contact = tk.StringVar()
        self.address = tk.StringVar()

        if self.editing_user:
             # Pre-fill fields
             self.user_id.set(self.editing_user.user_id)
             self.name.set(self.editing_user.name)
             self.role.set(self.editing_user.role)
             self.contact.set(self.editing_user.contact or "")
             self.address.set(self.editing_user.address or "")
             branch_obj = next((b for b in branches if b.branch_id == self.editing_user.branch_id), None)
             if branch_obj: self.branch.set(str(branch_obj))
             # Password field is left blank for editing for security
        else:
            # Default branch for new user? Maybe user's branch? Or first?
            if branches: self.branch.set(str(branches[0]))


        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        # User ID (disabled if editing)
        ttk.Label(main_frame, text="User ID:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        id_entry = ttk.Entry(main_frame, textvariable=self.user_id)
        id_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        if self.editing_user: id_entry.config(state=tk.DISABLED)
        row += 1

        # Password (required for add, optional for edit - means 'no change')
        pwd_label = "Password:*" if not self.editing_user else "New Password (leave blank if no change):"
        ttk.Label(main_frame, text=pwd_label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.password, show="*").grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        ttk.Label(main_frame, text="Full Name:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.name).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        ttk.Label(main_frame, text="Role:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Combobox(main_frame, textvariable=self.role, values=["EMPLOYEE", "MANAGER"], state="readonly").grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        ttk.Label(main_frame, text="Branch:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Combobox(main_frame, textvariable=self.branch, values=self.branches, state="readonly").grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        ttk.Label(main_frame, text="Contact:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.contact).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        ttk.Label(main_frame, text="Address:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.address).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        save_text = "Save User" # if not self.editing_user else "Update User" # TODO: Update logic
        ttk.Button(button_frame, text=save_text, command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=10)


    def _save(self):
        user_id = self.user_id.get().strip()
        password = self.password.get() # Get password, don't strip
        name = self.name.get().strip()
        role = self.role.get()
        branch_str = self.branch.get()
        contact = self.contact.get().strip()
        address = self.address.get().strip()

        # Basic Validation
        if not user_id or not name or not role or not branch_str:
             messagebox.showwarning("Input Error", "User ID, Name, Role, and Branch are required.", parent=self)
             return
        if not self.editing_user and not password: # Password required only when adding
             messagebox.showwarning("Input Error", "Password is required for new users.", parent=self)
             return

        selected_branch = next((b for b in self.branches if str(b) == branch_str), None)
        if not selected_branch:
             messagebox.showerror("Error", "Invalid branch selected.", parent=self)
             return

        if self.editing_user:
            # --- Update Logic (TODO) ---
            messagebox.showinfo("Not Implemented", "Update user functionality is not yet implemented.", parent=self)
            # 1. Create updated User object
            # 2. Check if password field is filled. If yes, call db.update_user_with_password(...)
            # 3. Else, call db.update_user_details(...) (needs to be created)
            # 4. Handle success/failure
            pass
        else:
            # --- Add Logic ---
            new_user = User(
                user_id=user_id, name=name, role=role, branch_id=selected_branch.branch_id,
                contact=contact or None, address=address or None
            )
            success = db.add_user(new_user, password) # Pass password separately for hashing
            if success:
                messagebox.showinfo("Success", f"User '{user_id}' added successfully.", parent=self)
                self.destroy()
            # else: Error shown by db function


# --- Add/Edit Branch Dialog ---
class AddEditBranchDialog(tk.Toplevel):
    def __init__(self, parent, branch_to_edit: Branch = None):
        super().__init__(parent)
        self.parent = parent
        self.editing_branch = branch_to_edit

        mode = "Edit" if self.editing_branch else "Add"
        self.title(f"{mode} Branch")
        self.geometry("450x300")
        self.grab_set()

        # Variables
        self.name = tk.StringVar()
        self.location = tk.StringVar()
        self.contact = tk.StringVar()
        self.address = tk.StringVar()

        if self.editing_branch:
             # Pre-fill
             self.name.set(self.editing_branch.name)
             self.location.set(self.editing_branch.location)
             self.contact.set(self.editing_branch.contact or "")
             self.address.set(self.editing_branch.address or "")

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Branch Name:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.name).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Location:*").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.location).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Contact:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.contact).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1
        ttk.Label(main_frame, text="Address:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(main_frame, textvariable=self.address).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=4)
        row += 1

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        save_text = "Save Branch" # if not self.editing_branch else "Update Branch" # TODO: Update logic
        ttk.Button(button_frame, text=save_text, command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def _save(self):
        name = self.name.get().strip()
        location = self.location.get().strip()
        contact = self.contact.get().strip()
        address = self.address.get().strip()

        if not name or not location:
            messagebox.showwarning("Input Error", "Branch Name and Location are required.", parent=self)
            return

        if self.editing_branch:
            # --- Update Logic (TODO) ---
            messagebox.showinfo("Not Implemented", "Update branch functionality is not yet implemented.", parent=self)
            # 1. Create updated Branch object (use existing branch_id)
            # 2. Call db.update_branch(...) function (needs to be created)
            # 3. Handle success/failure
            pass
        else:
            # --- Add Logic ---
            branch_id = db.generate_next_id('BR', 'branches', 'branch_id')
            new_branch = Branch(
                branch_id=branch_id, name=name, location=location,
                contact=contact or None, address=address or None
            )
            success = db.add_branch(new_branch)
            if success:
                 messagebox.showinfo("Success", f"Branch '{name}' ({branch_id}) added successfully.", parent=self)
                 self.destroy()
            # else: Error shown by db function