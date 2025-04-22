# TransportCompany_ComputerizationSoftware
# Transport Company Computerization Software (TCCS) - Python/Tkinter Version

## Overview

TCCS is a desktop application designed to streamline fleet management and consignment tracking for transport companies. It offers functionalities for managing company branches, users (employees/managers), the truck fleet, and individual consignments. Key features include real-time status updates, consignment allocation to trucks, basic revenue reporting, and analytics overview.

This project is a conversion of an original Java/Swing application to Python (3.7+), utilizing the Tkinter library (via `tkinter.ttk` for themed widgets) for the graphical user interface and MySQL as the relational database backend.

## Features

*   **User Authentication:** Secure login system.
*   **Role-Based Access:** Separate dashboards and functionalities for 'Manager' and 'Employee' roles.
*   **Consignment Management:**
    *   Create new consignments with sender/receiver details, volume, weight, etc.
    *   Calculate consignment charges based on defined rates.
    *   Generate and print/save consignment receipts.
    *   View consignments relevant to the user's branch.
    *   Update consignment status (Pending, In-Transit, Delivered, Cancelled).
    *   Allocate pending consignments to available trucks.
*   **Truck Fleet Management:**
    *   Add new trucks to the fleet.
    *   View details of all trucks (status, location, capacity, driver).
    *   Update truck status (Available, In-Transit, Maintenance) and location.
    *   View trucks available at the user's branch.
*   **Branch Management (Manager Role):**
    *   Add new company branches.
    *   View existing branches.
    *   *(Future: Edit/Delete Branches)*
*   **User Management (Manager Role):**
    *   Add new users (Managers or Employees).
    *   View existing users.
    *   *(Future: Edit/Delete Users)*
*   **Reporting & Analytics (Manager Role):**
    *   Generate a Revenue Report (total, branch-wise, monthly breakdown).
    *   Export Revenue Report to a text file.
    *   View an Analytics Summary (consignment counts, average waiting time, truck status counts, average idle time, total revenue).
*   **Database Integration:** Uses MySQL to persist all application data. Includes automatic database and table creation on first run.

## Technology Stack

*   **Language:** Python (3.7+)
*   **GUI:** Tkinter (`tkinter.ttk`)
*   **Database:** MySQL (5.7+ or 8.0+)
*   **Database Connector:** `mysql-connector-python`
*   **Password Hashing:** `bcrypt`

## Setup and Installation

1.  **Prerequisites:**
    *   Python (3.7 or newer recommended) installed.
    *   `pip` (Python package installer) available.
    *   MySQL Server installed and running.

2.  **Clone or Download:** Get the project code:
    ```bash
    git clone <repository_url> # Or download the ZIP file
    cd TCCS # Navigate to the project directory
    ```

3.  **Install Dependencies:**
    ```bash
    pip install mysql-connector-python bcrypt
    ```
    *(If you encounter SSL errors during installation, especially on older Python versions, you might need to use `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org mysql-connector-python bcrypt` or consider upgrading Python/pip).*

4.  **Database Configuration:**
    *   The application attempts to automatically create the database (`tccs_db`) and necessary tables on the first run.
    *   It uses the following **database credentials** by default (defined in `database_manager.py`):
        *   Host: `localhost`
        *   Port: `3306`
        *   User: `tccs_user`
        *   Password: `tccs_password`
    *   **IMPORTANT:** Ensure a MySQL user named `tccs_user` with the password `tccs_password` exists **OR** modify the `DB_CONFIG` dictionary in `database_manager.py` with your actual MySQL credentials.
    *   The MySQL user needs privileges to create databases and tables (at least initially). You might need to manually create the user and grant privileges if the script fails:
        ```sql
        -- Example SQL commands (run as MySQL root/admin user)
        CREATE USER 'tccs_user'@'localhost' IDENTIFIED BY 'tccs_password';
        CREATE DATABASE IF NOT EXISTS tccs_db;
        GRANT ALL PRIVILEGES ON tccs_db.* TO 'tccs_user'@'localhost';
        FLUSH PRIVILEGES;
        ```

## Usage

1.  **Run the Application:**
    ```bash
    python main.py
    ```

2.  **Login:**
    *   The application creates a default **administrator** account on the first run (if the database setup is successful).
    *   Use the following credentials to log in initially:
        *   **User ID:** `admin`
        *   **Password:** `admin123`

3.  **Explore:** Navigate through the tabs based on your user role (Manager or Employee).

## Database Details

*   **Database Name:** `tccs_db`
*   **Tables:** `branches`, `users`, `trucks`, `consignments`, `revenue` (Schema defined in `database_manager.py`)

## TODO / Future Enhancements

*   Implement Edit/Delete functionality for Users, Branches, and Trucks.
*   Implement the "Change Password" feature for users.
*   Add more robust input validation (e.g., formats for contact numbers, IDs).
*   Improve error handling and user feedback messages.
*   Consider moving database configuration to a separate file (`config.ini`, `.env`).
*   Add unit and integration tests.
*   Refine analytics and reporting features.
*   Potentially add expense tracking for profit calculation.
