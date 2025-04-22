
# database_manager.py
import mysql.connector
from mysql.connector import Error
import tkinter.messagebox as messagebox
import hashlib
import bcrypt # For better hashing
import atexit
from datetime import date

# --- Database Configuration ---
# IMPORTANT: Replace with your actual credentials or use environment variables/config file
DB_CONFIG = {
    'host': 'localhost',
    'user': 'tccs_user',         # Replace with your DB username
    'password': 'tccs_password', # Replace with your DB password
    'port': 3306
}
DB_NAME = 'tccs_db'

connection = None

# --- Helper Functions ---
def _hash_password(password):
    """Hashes a password using bcrypt."""
    if not password:
        return None
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8') # Store as string

def _verify_password(plain_password, hashed_password):
    """Verifies a plain password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Connection Management ---
def initialize():
    """Initializes the database connection, creates DB and tables if necessary."""
    global connection
    try:
        # 1. Connect to MySQL server (without specifying database)
        conn_server = mysql.connector.connect(**DB_CONFIG)
        cursor_server = conn_server.cursor()
        print("Connected to MySQL Server.")

        # 2. Create database if it doesn't exist
        cursor_server.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' checked/created.")
        cursor_server.close()
        conn_server.close()

        # 3. Connect to the specific database
        connection = mysql.connector.connect(
            **DB_CONFIG,
            database=DB_NAME
        )
        if connection.is_connected():
            print(f"Database connection established to '{DB_NAME}'.")
            _create_tables()
            _add_default_admin()
            atexit.register(close_connection) # Register cleanup on exit
        else:
             raise Error("Failed to connect to the database.")

    except Error as e:
        print(f"Database Error: {e}")
        messagebox.showerror("Database Error", f"Could not initialize database: {e}")
        exit(1) # Critical error

def get_connection():
    """Returns the database connection, attempts reconnect if closed."""
    global connection
    try:
        if connection is None or not connection.is_connected():
            print("Database connection lost. Attempting to reconnect...")
            connection = mysql.connector.connect(**DB_CONFIG, database=DB_NAME)
            if not connection.is_connected():
                raise Error("Reconnect failed.")
            print("Reconnected successfully.")
        return connection
    except Error as e:
        print(f"Error getting connection: {e}")
        messagebox.showerror("Database Error", f"Database connection error: {e}\nPlease restart the application.")
        # Depending on the error, might need to exit or handle differently
        return None # Indicate failure

def close_connection():
    """Closes the database connection."""
    global connection
    if connection and connection.is_connected():
        connection.close()
        print("Database connection closed.")

# --- Table Creation ---
def _create_tables():
    """Creates necessary tables if they don't exist."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        # Branches table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            branch_id VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            location VARCHAR(100) NOT NULL,
            contact VARCHAR(20),
            address VARCHAR(200)
        ) ENGINE=InnoDB;
        """)
        print("Branches table checked/created.")

        # Default Branch (Ensure it exists) - Use INSERT IGNORE
        cursor.execute("""
        INSERT IGNORE INTO branches (branch_id, name, location, contact, address)
        VALUES ('BR001', 'Main Branch', 'Headquarters', '+91-1234567890', 'Main Street, City');
        """)
        conn.commit() # Commit after insert ignore
        print("Default branch checked/added.")

        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(20) PRIMARY KEY,
            password VARCHAR(60) NOT NULL,
            name VARCHAR(100) NOT NULL,
            role ENUM('MANAGER', 'EMPLOYEE') NOT NULL,
            branch_id VARCHAR(20) NOT NULL,
            contact VARCHAR(20),
            address VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        ) ENGINE=InnoDB;
        """)
        print("Users table checked/created.")

        # Trucks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trucks (
            truck_id VARCHAR(20) PRIMARY KEY,
            registration_no VARCHAR(20) NOT NULL UNIQUE,
            capacity DOUBLE NOT NULL,
            driver_name VARCHAR(100),
            driver_contact VARCHAR(20),
            status ENUM('AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE') NOT NULL,
            current_location VARCHAR(100),
            source_branch VARCHAR(20),
            destination_branch VARCHAR(20) NULL,
            idle_since TIMESTAMP NULL,
            FOREIGN KEY (source_branch) REFERENCES branches(branch_id),
            FOREIGN KEY (destination_branch) REFERENCES branches(branch_id)
        ) ENGINE=InnoDB;
        """)
        print("Trucks table checked/created.")

        # Consignments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS consignments (
            consignment_id VARCHAR(20) PRIMARY KEY,
            volume DOUBLE NOT NULL,
            weight DOUBLE NOT NULL,
            type VARCHAR(50) NOT NULL,
            description VARCHAR(200),
            sender_name VARCHAR(100) NOT NULL,
            sender_address VARCHAR(200) NOT NULL,
            sender_contact VARCHAR(20) NOT NULL,
            sender_id VARCHAR(50) NOT NULL,
            receiver_name VARCHAR(100) NOT NULL,
            receiver_address VARCHAR(200) NOT NULL,
            receiver_contact VARCHAR(20) NOT NULL,
            receiver_id VARCHAR(50) NOT NULL,
            source_branch VARCHAR(20) NOT NULL,
            destination_branch VARCHAR(20) NOT NULL,
            truck_id VARCHAR(20) NULL,
            status ENUM('PENDING', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED') NOT NULL,
            charges DOUBLE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered_at TIMESTAMP NULL,
            FOREIGN KEY (source_branch) REFERENCES branches(branch_id),
            FOREIGN KEY (destination_branch) REFERENCES branches(branch_id),
            FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
        ) ENGINE=InnoDB;
        """)
        print("Consignments table checked/created.")

        # Revenue table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS revenue (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            branch_id VARCHAR(20) NOT NULL,
            amount DOUBLE NOT NULL,
            transaction_date DATE NOT NULL,
            description VARCHAR(200),
            consignment_id VARCHAR(20) NULL,
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
            FOREIGN KEY (consignment_id) REFERENCES consignments(consignment_id) ON DELETE SET NULL
        ) ENGINE=InnoDB;
        """)
        print("Revenue table checked/created.")
        conn.commit()

    except Error as e:
        print(f"Error creating tables: {e}")
        messagebox.showerror("Database Error", f"Error creating tables: {e}")
        conn.rollback() # Rollback on error
        exit(1)
    finally:
        if cursor:
            cursor.close()

def _add_default_admin():
    """Adds a default admin user if one doesn't exist."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        # Check if default branch exists (should exist after _create_tables)
        cursor.execute("SELECT COUNT(*) FROM branches WHERE branch_id = %s", ('BR001',))
        if cursor.fetchone()[0] == 0:
             print("Error: Default branch 'BR001' not found. Cannot add admin.")
             return # Should not happen if tables created correctly

        # Check if admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", ('admin',))
        count = cursor.fetchone()[0]

        if count == 0:
            hashed_pw = _hash_password("admin123")
            if hashed_pw:
                sql = """
                INSERT INTO users (user_id, password, name, role, branch_id, contact, address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = ('admin', hashed_pw, 'System Administrator', 'MANAGER', 'BR001', '+91-9876543210', 'Admin Office, Headquarters')
                cursor.execute(sql, values)
                conn.commit()
                print("Default admin (admin/admin123) created.")
            else:
                print("Error hashing default admin password.")
        else:
             print("Default admin 'admin' already exists.")

    except Error as e:
        print(f"Error adding/checking default admin: {e}")
        messagebox.showerror("Database Error", f"Error setting up default admin: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()

# --- CRUD Operations (Example: User Authentication) ---
def authenticate_user(user_id, password):
    """Authenticates a user against the database."""
    # Import here to avoid circular dependency if models import database_manager
    from models import User

    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True) # Fetch as dict
    user = None
    try:
        sql = "SELECT * FROM users WHERE user_id = %s"
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()

        if result:
            stored_password_hash = result.get("password")
            if _verify_password(password, stored_password_hash):
                # Password matches, create User object
                user = User(
                    user_id=result['user_id'],
                    # password=stored_password_hash, # Don't store hash in the model object usually
                    name=result['name'],
                    role=result['role'],
                    branch_id=result['branch_id'],
                    contact=result.get('contact'), # Use get for nullable fields
                    address=result.get('address')
                )
                print(f"User '{user_id}' authenticated successfully.")
            else:
                print(f"Authentication failed for user '{user_id}': Incorrect password.")
        else:
             print(f"Authentication failed for user '{user_id}': User not found.")

    except Error as e:
        print(f"Authentication error: {e}")
        messagebox.showerror("Authentication Error", f"Database error during login: {e}")
    finally:
        if cursor:
            cursor.close()
    return user # Return User object or None


# --- Add other CRUD functions from Java (adapting SQL and error handling) ---

def add_user(user, password):
    """Adds a new user to the database."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False
    hashed_pw = _hash_password(password)
    if not hashed_pw:
        messagebox.showerror("Error", "Could not hash password.")
        return False

    sql = """
    INSERT INTO users (user_id, password, name, role, branch_id, contact, address)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (user.user_id, hashed_pw, user.name, user.role, user.branch_id, user.contact, user.address)
    try:
        cursor.execute(sql, values)
        conn.commit()
        success = cursor.rowcount > 0
        if success:
             print(f"User '{user.user_id}' added successfully.")
    except Error as e:
        print(f"Error adding user: {e}")
        messagebox.showerror("Database Error", f"Error adding user '{user.user_id}':\n{e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
    return success

def get_all_users():
    """Fetches all users from the database."""
    from models import User # Avoid circular import
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    users = []
    try:
        cursor.execute("SELECT user_id, name, role, branch_id, contact, address FROM users ORDER BY name")
        results = cursor.fetchall()
        for row in results:
             users.append(User(
                 user_id=row['user_id'],
                 name=row['name'],
                 role=row['role'],
                 branch_id=row['branch_id'],
                 contact=row.get('contact'),
                 address=row.get('address')
             ))
    except Error as e:
        print(f"Error fetching users: {e}")
        messagebox.showerror("Database Error", f"Error fetching users: {e}")
    finally:
        if cursor:
            cursor.close()
    return users

def get_all_branches():
    """Fetches all branches from the database."""
    from models import Branch # Avoid circular import
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    branches = []
    try:
        cursor.execute("SELECT * FROM branches ORDER BY branch_id")
        results = cursor.fetchall()
        for row in results:
            branches.append(Branch(
                branch_id=row['branch_id'],
                name=row['name'],
                location=row['location'],
                contact=row.get('contact'),
                address=row.get('address')
            ))
    except Error as e:
        print(f"Error fetching branches: {e}")
        messagebox.showerror("Database Error", f"Error fetching branches: {e}")
    finally:
        if cursor:
            cursor.close()
    return branches

def add_branch(branch):
    """Adds a new branch to the database."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False
    sql = """
    INSERT INTO branches (branch_id, name, location, contact, address)
    VALUES (%s, %s, %s, %s, %s)
    """
    values = (branch.branch_id, branch.name, branch.location, branch.contact, branch.address)
    try:
        cursor.execute(sql, values)
        conn.commit()
        success = cursor.rowcount > 0
        if success:
             print(f"Branch '{branch.name}' ({branch.branch_id}) added successfully.")
    except Error as e:
        print(f"Error adding branch: {e}")
        messagebox.showerror("Database Error", f"Error adding branch '{branch.name}':\n{e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
    return success

def generate_next_id(prefix, table, column):
    """Generates the next sequential ID based on a prefix (e.g., BR001, TR001)."""
    conn = get_connection()
    if not conn: return f"{prefix}001" # Default fallback
    cursor = conn.cursor()
    next_id_str = f"{prefix}001" # Default if table is empty
    try:
        # Ensure column has the prefix and the rest is numeric
        # This query might need adjustment based on exact ID format and DB engine
        # Using MAX(CAST(SUBSTRING(...) AS UNSIGNED)) is MySQL specific
        sql = f"""
        SELECT MAX(CAST(SUBSTRING({column}, {len(prefix) + 1}) AS UNSIGNED))
        FROM {table}
        WHERE {column} LIKE '{prefix}%'
        """
        cursor.execute(sql)
        result = cursor.fetchone()
        if result and result[0] is not None:
            next_id_num = int(result[0]) + 1
            # Determine padding based on prefix length or a fixed width
            padding = 3 if prefix in ('BR', 'TR') else 4 # Example: BR001, CON0001
            next_id_str = f"{prefix}{next_id_num:0{padding}d}"

    except Error as e:
        print(f"Error generating next ID for {prefix}: {e}")
        # Return default on error
    except (ValueError, TypeError) as e:
         print(f"Error parsing existing IDs for {prefix}: {e}")
         # Return default if parsing fails
    finally:
        if cursor:
            cursor.close()
    # print(f"Generated next ID: {next_id_str}") # Debugging
    return next_id_str

# --- Add remaining CRUD functions for Truck, Consignment, Revenue ---
# --- (get_all, add, update, find_available, get_by_id, etc.) ---
# --- These will follow similar patterns: get connection, create cursor, ---
# --- execute SQL with parameters, commit/rollback, handle errors, close cursor ---
# --- Remember to import models locally within functions or pass model classes ---

def add_truck(truck):
    """Adds a new truck."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False
    sql = """
    INSERT INTO trucks (truck_id, registration_no, capacity, driver_name, driver_contact,
                        status, current_location, source_branch, destination_branch, idle_since)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (truck.truck_id, truck.registration_no, truck.capacity, truck.driver_name,
              truck.driver_contact, truck.status, truck.current_location, truck.source_branch,
              truck.destination_branch, truck.idle_since)
    try:
        cursor.execute(sql, values)
        conn.commit()
        success = cursor.rowcount > 0
        if success: print(f"Truck '{truck.truck_id}' added.")
    except Error as e:
        print(f"Error adding truck: {e}")
        messagebox.showerror("Database Error", f"Error adding truck:\n{e}")
        conn.rollback()
    finally:
        cursor.close()
    return success

def get_all_trucks():
    """Fetches all trucks."""
    from models import Truck
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    trucks = []
    try:
        cursor.execute("SELECT * FROM trucks ORDER BY truck_id")
        results = cursor.fetchall()
        for row in results:
            trucks.append(Truck(**row)) # Use dictionary unpacking
    except Error as e:
        print(f"Error fetching trucks: {e}")
        messagebox.showerror("Database Error", f"Error fetching trucks: {e}")
    finally:
        cursor.close()
    return trucks

def get_available_trucks_by_branch(branch_id):
    """Fetches available trucks at a specific branch."""
    from models import Truck
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    trucks = []
    sql = "SELECT * FROM trucks WHERE status = 'AVAILABLE' AND source_branch = %s ORDER BY capacity"
    try:
        cursor.execute(sql, (branch_id,))
        results = cursor.fetchall()
        for row in results:
            trucks.append(Truck(**row))
    except Error as e:
        print(f"Error fetching available trucks: {e}")
        messagebox.showerror("Database Error", f"Error fetching available trucks: {e}")
    finally:
        cursor.close()
    return trucks

def update_truck_status(truck_id, new_status, new_destination_branch, new_source_branch):
    """Updates truck status, location, and potentially idle time."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False

    # Get branch location for current_location field
    branch_location = new_source_branch # Default
    try:
        cursor.execute("SELECT location FROM branches WHERE branch_id = %s", (new_source_branch,))
        result = cursor.fetchone()
        if result:
            branch_location = result[0]
    except Error as e:
         print(f"Could not fetch branch location for truck update: {e}")
         # Proceed with branch_id as location

    sql = """
    UPDATE trucks
    SET status = %s,
        destination_branch = %s,
        source_branch = %s,
        current_location = %s,
        idle_since = CASE WHEN %s = 'AVAILABLE' THEN CURRENT_TIMESTAMP ELSE NULL END
    WHERE truck_id = %s
    """
    # Destination is only set if IN_TRANSIT
    dest_val = new_destination_branch if new_status == 'IN_TRANSIT' else None
    values = (new_status, dest_val, new_source_branch, branch_location, new_status, truck_id)

    try:
        cursor.execute(sql, values)
        conn.commit()
        success = cursor.rowcount > 0
        if success: print(f"Truck {truck_id} status updated to {new_status}.")
        else: print(f"Truck {truck_id} not found or status not changed.")
    except Error as e:
        print(f"Error updating truck status: {e}")
        messagebox.showerror("Database Error", f"Error updating truck status:\n{e}")
        conn.rollback()
    finally:
        cursor.close()
    return success

# --- Consignment Functions ---

def add_consignment(consignment):
    """Adds a new consignment."""
    conn = get_connection()
    if not conn: return False, None # Return success, id
    cursor = conn.cursor()
    success = False
    consignment_id = consignment.consignment_id # Already generated

    sql = """
    INSERT INTO consignments (consignment_id, volume, weight, type, description,
                              sender_name, sender_address, sender_contact, sender_id,
                              receiver_name, receiver_address, receiver_contact, receiver_id,
                              source_branch, destination_branch, truck_id, status, charges,
                              created_at, delivered_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        consignment_id, consignment.volume, consignment.weight, consignment.type, consignment.description,
        consignment.sender_name, consignment.sender_address, consignment.sender_contact, consignment.sender_id,
        consignment.receiver_name, consignment.receiver_address, consignment.receiver_contact, consignment.receiver_id,
        consignment.source_branch, consignment.destination_branch, consignment.truck_id, consignment.status,
        consignment.charges, consignment.created_at, consignment.delivered_at
    )
    try:
        cursor.execute(sql, values)
        # Record revenue if charges > 0
        if consignment.charges > 0:
            _record_revenue(cursor, consignment) # Pass cursor for transaction
        conn.commit()
        success = cursor.rowcount > 0
        if success: print(f"Consignment '{consignment_id}' created.")
    except Error as e:
        print(f"Error creating consignment: {e}")
        messagebox.showerror("Database Error", f"Error creating consignment:\n{e}")
        conn.rollback()
        consignment_id = None # Indicate failure
    finally:
        cursor.close()
    return success, consignment_id

def _record_revenue(cursor, consignment):
    """Internal function to record revenue within a transaction."""
    sql_revenue = """
    INSERT INTO revenue (branch_id, amount, transaction_date, description, consignment_id)
    VALUES (%s, %s, CURDATE(), %s, %s)
    """
    # Ensure date is handled correctly, CURDATE() is MySQL specific
    desc = f"Charges for consignment {consignment.consignment_id}"
    values_revenue = (consignment.source_branch, consignment.charges, desc, consignment.consignment_id)
    try:
        cursor.execute(sql_revenue, values_revenue)
        print(f"Revenue recorded for consignment {consignment.consignment_id}")
    except Error as e:
        print(f"Error recording revenue for {consignment.consignment_id}: {e}")
        # Raise the error to trigger rollback in the calling function
        raise e

def get_consignments_by_branch(branch_id):
    """Fetches consignments originating from or destined for a branch."""
    from models import Consignment
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    consignments = []
    sql = "SELECT * FROM consignments WHERE source_branch = %s OR destination_branch = %s ORDER BY created_at DESC"
    try:
        cursor.execute(sql, (branch_id, branch_id))
        results = cursor.fetchall()
        for row in results:
            consignments.append(Consignment(**row))
    except Error as e:
        print(f"Error fetching consignments for branch {branch_id}: {e}")
        messagebox.showerror("Database Error", f"Error fetching consignments: {e}")
    finally:
        cursor.close()
    return consignments

def get_all_consignments():
    """Fetches all consignments."""
    from models import Consignment
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    consignments = []
    sql = "SELECT * FROM consignments ORDER BY created_at DESC"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            consignments.append(Consignment(**row))
    except Error as e:
        print(f"Error fetching all consignments: {e}")
        messagebox.showerror("Database Error", f"Error fetching consignments: {e}")
    finally:
        cursor.close()
    return consignments


def get_consignment_by_id(consignment_id):
    """Fetches a single consignment by its ID."""
    from models import Consignment
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    consignment = None
    sql = "SELECT * FROM consignments WHERE consignment_id = %s"
    try:
        cursor.execute(sql, (consignment_id,))
        result = cursor.fetchone()
        if result:
            consignment = Consignment(**result)
    except Error as e:
        print(f"Error fetching consignment {consignment_id}: {e}")
        messagebox.showerror("Database Error", f"Error fetching consignment: {e}")
    finally:
        cursor.close()
    return consignment

def update_consignment_status(consignment_id, new_status):
    """Updates consignment status and potentially delivered_at timestamp."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False

    try:
        conn.start_transaction()

        # Update consignment status
        if new_status == 'DELIVERED':
            sql_update = "UPDATE consignments SET status = %s, delivered_at = CURRENT_TIMESTAMP WHERE consignment_id = %s"
        else:
            # Reset delivered_at if status changes from DELIVERED or to something else
            sql_update = "UPDATE consignments SET status = %s, delivered_at = NULL WHERE consignment_id = %s"
        cursor.execute(sql_update, (new_status, consignment_id))
        updated_rows = cursor.rowcount

        if updated_rows > 0:
            print(f"Consignment {consignment_id} status updated to {new_status}.")

            # If DELIVERED, check if truck can be made available
            if new_status == 'DELIVERED':
                # Find truck and destination branch for this consignment
                cursor.execute("SELECT truck_id, destination_branch FROM consignments WHERE consignment_id = %s", (consignment_id,))
                result = cursor.fetchone()
                if result:
                    truck_id, dest_branch = result
                    if truck_id and dest_branch:
                         # Check if other consignments are still IN_TRANSIT on the same truck
                        cursor.execute("SELECT COUNT(*) FROM consignments WHERE truck_id = %s AND status = 'IN_TRANSIT'", (truck_id,))
                        other_consignments_count = cursor.fetchone()[0]

                        if other_consignments_count == 0:
                            # No other consignments in transit, update truck status (using direct SQL within transaction)
                             # Get branch location
                             branch_location = dest_branch
                             try:
                                 cursor.execute("SELECT location FROM branches WHERE branch_id = %s", (dest_branch,))
                                 loc_res = cursor.fetchone()
                                 if loc_res: branch_location = loc_res[0]
                             except Error as loc_e:
                                 print(f"Could not fetch branch location for truck update: {loc_e}")

                             sql_truck = """
                             UPDATE trucks SET status = 'AVAILABLE', destination_branch = NULL,
                                            source_branch = %s, current_location = %s,
                                            idle_since = CURRENT_TIMESTAMP
                             WHERE truck_id = %s
                             """
                             cursor.execute(sql_truck, (dest_branch, branch_location, truck_id))
                             if cursor.rowcount > 0:
                                 print(f"Truck {truck_id} status set to AVAILABLE at branch {dest_branch}.")
                             else:
                                 print(f"Truck {truck_id} not found or status update failed.")
                                 # Raise error? Or just log? Depends on severity.
                                 # raise Error(f"Failed to update truck {truck_id} status after delivery.")
                        else:
                            print(f"Truck {truck_id} still has {other_consignments_count} consignments in transit.")
            conn.commit()
            success = True
        else:
             print(f"Consignment {consignment_id} not found or status not changed.")
             conn.rollback() # Nothing was updated

    except Error as e:
        print(f"Error updating consignment status for {consignment_id}: {e}")
        messagebox.showerror("Database Error", f"Error updating consignment status:\n{e}")
        try:
            conn.rollback()
        except Error as rb_e:
            print(f"Rollback failed: {rb_e}")
        success = False
    finally:
        cursor.close()
    return success

def get_total_pending_volume(source_branch, destination_branch):
    """Calculates total volume of pending consignments for a route."""
    conn = get_connection()
    if not conn: return 0.0
    cursor = conn.cursor()
    total_volume = 0.0
    sql = """
    SELECT SUM(volume) FROM consignments
    WHERE source_branch = %s AND destination_branch = %s
      AND status = 'PENDING' AND truck_id IS NULL
    """
    try:
        cursor.execute(sql, (source_branch, destination_branch))
        result = cursor.fetchone()
        if result and result[0] is not None:
            total_volume = float(result[0])
    except Error as e:
        print(f"Error calculating pending volume: {e}")
        messagebox.showerror("Database Error", f"Error calculating pending volume:\n{e}")
    except (ValueError, TypeError):
         print("Error converting pending volume sum.") # Should be numeric
    finally:
        cursor.close()
    return total_volume

def allocate_truck_to_consignments(source_branch, destination_branch, truck_id):
    """Assigns a truck to pending consignments and updates statuses."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    success = False

    try:
        conn.start_transaction()

        # 1. Update consignments
        sql_update_cons = """
        UPDATE consignments SET truck_id = %s, status = 'IN_TRANSIT'
        WHERE source_branch = %s AND destination_branch = %s
          AND status = 'PENDING' AND truck_id IS NULL
        """
        cursor.execute(sql_update_cons, (truck_id, source_branch, destination_branch))
        updated_consignments = cursor.rowcount

        if updated_consignments > 0:
            print(f"{updated_consignments} consignments allocated to truck {truck_id}.")

            # 2. Update truck status
            # Get source branch location
            branch_location = source_branch
            try:
                cursor.execute("SELECT location FROM branches WHERE branch_id = %s", (source_branch,))
                loc_res = cursor.fetchone()
                if loc_res: branch_location = loc_res[0]
            except Error as loc_e:
                print(f"Could not fetch branch location for truck update: {loc_e}")

            sql_update_truck = """
            UPDATE trucks SET status = 'IN_TRANSIT', destination_branch = %s,
                           source_branch = %s, current_location = %s, idle_since = NULL
            WHERE truck_id = %s AND status = 'AVAILABLE'
            """
            # Only update truck if it's currently available
            cursor.execute(sql_update_truck, (destination_branch, source_branch, branch_location, truck_id))

            if cursor.rowcount > 0:
                print(f"Truck {truck_id} status updated to IN_TRANSIT to {destination_branch}.")
                conn.commit()
                success = True
            else:
                print(f"Failed to update truck {truck_id} status (maybe not AVAILABLE or not found). Rolling back.")
                conn.rollback()
                messagebox.showerror("Allocation Error", f"Failed to update status for Truck {truck_id}. Ensure it is AVAILABLE at {source_branch}.")
        else:
            print(f"No pending consignments found for route {source_branch} -> {destination_branch}.")
            conn.rollback() # Nothing changed, but good practice
            messagebox.showinfo("Allocation Info", "No pending consignments found for the selected route.")

    except Error as e:
        print(f"Error allocating truck: {e}")
        messagebox.showerror("Database Error", f"Error allocating truck:\n{e}")
        try:
            conn.rollback()
        except Error as rb_e:
            print(f"Rollback failed: {rb_e}")
        success = False
    finally:
        cursor.close()
    return success

# --- Revenue Functions ---
def get_all_revenue_transactions():
    """Fetches all revenue transactions."""
    from models import Revenue # Avoid circular import
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    transactions = []
    try:
        cursor.execute("SELECT * FROM revenue ORDER BY transaction_date DESC, transaction_id DESC")
        results = cursor.fetchall()
        for row in results:
             # Ensure date is handled correctly
             trans_date = row['transaction_date']
             if isinstance(trans_date, str): # Handle potential string dates
                 trans_date = date.fromisoformat(trans_date)

             transactions.append(Revenue(
                transaction_id=row['transaction_id'],
                branch_id=row['branch_id'],
                amount=row['amount'],
                transaction_date=trans_date, # Should be datetime.date object
                description=row.get('description'),
                consignment_id=row.get('consignment_id')
             ))
    except Error as e:
        print(f"Error fetching revenue transactions: {e}")
        messagebox.showerror("Database Error", f"Error fetching revenue: {e}")
    finally:
        if cursor: cursor.close()
    return transactions

def get_total_revenue():
    """Calculates total revenue across all branches."""
    conn = get_connection()
    if not conn: return 0.0
    cursor = conn.cursor()
    total = 0.0
    try:
        cursor.execute("SELECT SUM(amount) FROM revenue")
        result = cursor.fetchone()
        if result and result[0] is not None:
            total = float(result[0])
    except Error as e:
        print(f"Error calculating total revenue: {e}")
        messagebox.showerror("Database Error", f"Error calculating total revenue: {e}")
    finally:
        if cursor: cursor.close()
    return total

def get_total_revenue_by_branch(branch_id):
    """Calculates total revenue for a specific branch."""
    conn = get_connection()
    if not conn: return 0.0
    cursor = conn.cursor()
    total = 0.0
    sql = "SELECT SUM(amount) FROM revenue WHERE branch_id = %s"
    try:
        cursor.execute(sql, (branch_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            total = float(result[0])
    except Error as e:
        print(f"Error calculating branch revenue for {branch_id}: {e}")
        messagebox.showerror("Database Error", f"Error calculating branch revenue: {e}")
    finally:
        if cursor: cursor.close()
    return total

def get_revenue_by_period(start_date, end_date):
    """Calculates revenue within a date range (inclusive)."""
    conn = get_connection()
    if not conn: return 0.0
    cursor = conn.cursor()
    total = 0.0
    sql = "SELECT SUM(amount) FROM revenue WHERE transaction_date BETWEEN %s AND %s"
    try:
        # Ensure dates are in correct format (YYYY-MM-DD string or date objects)
        cursor.execute(sql, (start_date, end_date))
        result = cursor.fetchone()
        if result and result[0] is not None:
            total = float(result[0])
    except Error as e:
        print(f"Error calculating revenue by period: {e}")
        messagebox.showerror("Database Error", f"Error calculating revenue by period: {e}")
    finally:
        if cursor: cursor.close()
    return total