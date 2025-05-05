# conftest.py (Reverted - Modifies Global App Config)

import pytest
# --- Import global app and db instance from app.py ---
from app import app as flask_app, db as sqlalchemy_db
# Import models (needed globally here for this structure)
from app import Branch, User, Truck, Consignment, ConsignmentTruck, TruckAssignment
import os
import tempfile
import bcrypt
import sqlite3

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application using temp file DB"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    print(f"--- Using Test DB: {db_path} ---")

    # --- CRITICAL: Update config on the IMPORTED app object ---
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": 'test-secret-key',
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    # --- Force SQLAlchemy Engine Recreation (Workaround) ---
    # Dispose existing engine potentially connected to dev DB
    if sqlalchemy_db.engine:
        sqlalchemy_db.engine.dispose()
    # Create a new engine explicitly using the updated config
    sqlalchemy_db.engine = sqlalchemy_db.create_engine(flask_app.config['SQLALCHEMY_DATABASE_URI'], {})
    print("--- App Configured for Testing & Engine Recreated ---")
    print(f"--- Engine Recreated: {sqlalchemy_db.engine} ---") # Verify it points to temp DB

    with flask_app.app_context():
        print("--- Creating all tables... ---")
        try:
            # Attempt to drop tables first (might fail if DB was empty)
            try:
                sqlalchemy_db.drop_all()
                print("--- Dropped existing tables (if any). ---")
            except Exception as drop_err:
                print(f"Info: Pre-test drop_all failed (might be ok): {drop_err}")

            # Create tables using the recreated engine
            sqlalchemy_db.create_all()
            print("--- create_all finished. ---")

            # --- Schema Inspection ---
            print("--- Inspecting created schema... ---")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"Tables found in DB file: {tables}")
                conn.close()
                print("--- Schema inspection complete. ---")
            except Exception as inspect_e:
                 print(f"!!! ERROR DURING SCHEMA INSPECTION: {inspect_e} !!!")
            # --- End Schema Inspection ---

        except Exception as e:
            print(f"!!! ERROR DURING create_all: {e} !!!")
            import traceback
            traceback.print_exc()
            raise e

    yield flask_app

    # Teardown
    print(f"--- Cleaning up Test DB: {db_path} ---")
    # No need to drop tables here if db_session cleans up per function
    try:
        os.close(db_fd)
    except OSError: pass
    try:
        os.unlink(db_path)
        print(f"--- Deleted test DB file: {db_path} ---")
    except Exception as unlink_e:
        print(f"Warning: Failed to delete test db file {db_path}: {unlink_e}")


# --- client fixture ---
@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

# --- db fixture ---
@pytest.fixture(scope='session')
def db(app):
    return sqlalchemy_db

# --- db_session Fixture (Simpler version, relies on Flask-SQLAlchemy session proxy) ---
@pytest.fixture(scope='function')
def db_session(app, db):
    """Provides database session access, clears tables, seeds branches."""
    with app.app_context():
        # Clear data using DELETE FROM
        print("--- Fixture db_session: Clearing tables (DELETE FROM)... ---")
        conn = db.engine.connect()
        trans = conn.begin()
        try:
            for table in reversed(db.metadata.sorted_tables):
                conn.execute(table.delete())
            trans.commit()
            print("--- Fixture db_session: Table clearing committed. ---")
        except Exception as e:
            trans.rollback()
            print(f"Error clearing tables: {e}")
            raise e
        finally:
            conn.close() # Close connection used for clearing

        # Seed essential branches
        print("--- Fixture db_session: Seeding branches... ---")
        b1_exists = db.session.get(Branch, 'branch-capital')
        b2_exists = db.session.get(Branch, 'branch-citya')
        if not b1_exists: db.session.add(Branch(id='branch-capital', location='Capital'))
        if not b2_exists: db.session.add(Branch(id='branch-citya', location='CityA'))
        if not b1_exists or not b2_exists:
            try:
                db.session.commit()
                print("--- Fixture db_session: Branch seeding committed. ---")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing branch seed: {e}")
                raise e
        else:
            print("--- Fixture db_session: Branches already seeded. ---")

        yield db.session # Provide Flask-SQLAlchemy's session proxy

        # Teardown: Rollback anything done during test, remove session
        print(f"--- Fixture db_session: Tearing down (rollback/remove) ---")
        db.session.rollback() # Rollback changes made *during* the test
        db.session.remove()


# --- ensure_manager_exists ---
@pytest.fixture(scope='function')
def ensure_manager_exists(db_session):
    manager = db_session.query(User).filter_by(username='manager1').first()
    if not manager:
        print("--- Fixture ensure_manager_exists: Creating manager1 ---")
        hashed_pwd = bcrypt.hashpw('managerpass'.encode('utf-8'), bcrypt.gensalt())
        manager = User(username='manager1', password=hashed_pwd.decode('utf-8'), role='Manager')
        db_session.add(manager)
        try:
            db_session.commit()
            print(f"--- Fixture ensure_manager_exists: manager1 committed (ID: {manager.id}) ---")
        except Exception as e:
            db_session.rollback()
            pytest.fail(f"Failed to create manager user in fixture: {e}")
    else:
         print(f"--- Fixture ensure_manager_exists: manager1 already exists (ID: {manager.id}) ---")
    yield manager

# --- logged_in_manager ---
@pytest.fixture
def logged_in_manager(client, ensure_manager_exists):
     print("--- Fixture: logged_in_manager: Logging in... ---")
     res = client.post('/login', data={'username': 'manager1', 'password': 'managerpass'})
     if res.status_code >= 300:
         pytest.fail(f"Login failed within logged_in_manager fixture. Status: {res.status_code}. Data: {res.data.decode(errors='ignore')[:200]}")
     print("--- Fixture: logged_in_manager: Login POST sent. ---")
     yield client
     print("--- Fixture: logged_in_manager: Logging out... ---")
     res_logout = client.get('/logout')
     print(f"--- Fixture: logged_in_manager: Logout GET sent (Status: {res_logout.status_code}). ---")

# --- ensure_employee_exists ---
@pytest.fixture(scope='function')
def ensure_employee_exists(db_session):
    city_a_branch_id = 'branch-citya'
    city_a_branch = db_session.query(Branch).filter_by(id=city_a_branch_id).first()
    if not city_a_branch:
         # This might fail if the branch seeding above had issues
         pytest.fail(f"Required branch '{city_a_branch_id}' not found during ensure_employee_exists setup.")
    employee = db_session.query(User).filter_by(username='employee1').first()
    if not employee:
        print("--- Fixture ensure_employee_exists: Creating employee1 ---")
        hashed_pwd = bcrypt.hashpw('employeepass'.encode('utf-8'), bcrypt.gensalt())
        employee = User(username='employee1', password=hashed_pwd.decode('utf-8'), role='Employee', branch_id=city_a_branch.id)
        db_session.add(employee)
        try:
            db_session.commit()
            print(f"--- Fixture ensure_employee_exists: employee1 committed (ID: {employee.id}) ---")
        except Exception as e:
            db_session.rollback()
            pytest.fail(f"Failed to create employee user in fixture: {e}")
    else:
         print(f"--- Fixture ensure_employee_exists: employee1 already exists (ID: {employee.id}) ---")
    yield employee

# --- ensure_truck_citya1_exists ---
@pytest.fixture
def ensure_truck_citya1_exists(db_session):
    truck_id = 'truck-citya1'
    branch_id = 'branch-citya'
    truck = db_session.get(Truck, truck_id)
    if not truck:
        print(f"--- Fixture ensure_truck_citya1_exists: Creating truck {truck_id} ---")
        truck = Truck(id=truck_id, location='CityA Depot Test Fixture', branch_id=branch_id, status='Available', capacity=500)
        db_session.add(truck)
        try:
            db_session.commit()
            print(f"--- Fixture ensure_truck_citya1_exists: Truck {truck_id} committed ---")
        except Exception as e:
            db_session.rollback()
            pytest.fail(f"Failed to create truck {truck_id} in fixture: {e}")
    else:
        truck.status = 'Available' # Ensure status is correct for test
        try:
             db_session.commit()
        except Exception as e:
             db_session.rollback() # Rollback if status update fails
             print(f"Warning: Failed to commit truck status update for {truck_id}: {e}")
        print(f"--- Fixture ensure_truck_citya1_exists: Truck {truck_id} exists ---")
    return truck