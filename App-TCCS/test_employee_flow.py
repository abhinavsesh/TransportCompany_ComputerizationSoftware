# tests/test_employee_flow.py (State for 7 Passed / 6 Errors)

import pytest
from app import User, Consignment, Truck, ConsignmentTruck # Import necessary models

# Fixtures like ensure_truck_citya1_exists are defined in conftest.py

# --- Tests ---

def test_manager_view_dashboard(logged_in_manager):
    """Test manager can access their dashboard."""
    print("\n--- Test: test_manager_view_dashboard ---")
    response = logged_in_manager.get('/dashboard')
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    assert b"Manager Dashboard" in response.data

def test_manager_add_employee(logged_in_manager, db_session):
    """Test manager can successfully add a new employee."""
    print("\n--- Test: test_manager_add_employee ---")
    new_username = 'test_emp_add_success'
    employee_data = {
        'username': new_username,
        'password': 'testpassword',
        'branch_id': 'branch-citya' # Assumes seeded by db_session
    }
    print(f"Attempting to add employee: {employee_data}")
    response = logged_in_manager.post('/employees', json=employee_data)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Data: {response.data.decode(errors='ignore')}")

    assert response.status_code == 201 # Expect 201 Created

    # Verify user exists in DB with correct details
    new_user = db_session.query(User).filter_by(username=new_username).first()
    assert new_user is not None, f"User '{new_username}' not found."
    assert new_user.role == 'Employee'
    assert new_user.branch_id == 'branch-citya'
    print(f"Verified user '{new_username}' added successfully.")

def test_manager_add_employee_duplicate_username(logged_in_manager, db_session, ensure_employee_exists):
    """Test adding employee with existing username fails."""
    existing_username = ensure_employee_exists.username
    print(f"\n--- Test: test_manager_add_employee_duplicate_username ---")
    employee_data = {
        'username': existing_username, # Use existing username 'employee1'
        'password': 'newpassword',
        'branch_id': 'branch-citya'
    }
    print(f"Attempting to add duplicate employee: {employee_data}")
    response = logged_in_manager.post('/employees', json=employee_data)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Data: {response.data.decode(errors='ignore')}")

    # --- THIS IS LIKELY WHERE ONE OF THE FAILURES OCCURRED ---
    # Original test might have asserted 201 == 400
    # Your route now correctly returns 400 if duplicate exists.
    assert response.status_code == 400
    assert b"Username already exists" in response.data

def test_manager_get_consignments(logged_in_manager, db_session):
    """Test manager sees consignments from all branches."""
    print(f"\n--- Test: test_manager_get_consignments ---")
    cons_id_1 = 'cons-get-test-1'
    cons_id_2 = 'cons-get-test-2'
    # db_session fixture seeds branches 'branch-citya' and 'branch-capital'
    c1 = Consignment(id=cons_id_1, volume=5, destination='Capital', sender_name='C1', sender_address='SA1', receiver_name='R1', receiver_address='RA1', charge=50, branch_id='branch-citya')
    c2 = Consignment(id=cons_id_2, volume=8, destination='CityB', sender_name='C2', sender_address='SA2', receiver_name='R2', receiver_address='RA2', charge=80, branch_id='branch-capital')
    db_session.add_all([c1, c2])

    # --- THIS IS LIKELY WHERE AN OperationalError FAILURE OCCURRED ---
    # If the engine points to the wrong DB OR the schema is wrong in the temp DB
    try:
        db_session.commit()
        print(f"Added test consignments: {cons_id_1}, {cons_id_2}")
    except Exception as e:
        print(f"!!! Error during commit in test_manager_get_consignments: {e} !!!")
        pytest.fail(f"Commit failed, likely schema issue: {e}")


    print("Making GET request to /consignments")
    response = logged_in_manager.get('/consignments')
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    print(f"Received {len(data)} consignments.")
    consignment_ids_in_response = {c['id'] for c in data}
    assert cons_id_1 in consignment_ids_in_response
    assert cons_id_2 in consignment_ids_in_response
    print("Verified both test consignments are present.")

def test_manager_assign_consignment_success(logged_in_manager, db_session, ensure_truck_citya1_exists):
    """Test manager successfully assigns a pending consignment to a truck."""
    truck = ensure_truck_citya1_exists # Fixture ensures truck exists in branch-citya
    cons_id = 'cons-assign-test-ok'
    print(f"\n--- Test: test_manager_assign_consignment_success ---")
    print(f"Using truck: {truck.id} in branch {truck.branch_id}")

    cons = Consignment(
        id=cons_id, volume=50, destination='Capital', sender_name='Assign Sender',
        sender_address='AS1', receiver_name='AR1', receiver_address='AR1', charge=500,
        branch_id=truck.branch_id, status='Pending' # Same branch as truck
    )
    db_session.add(cons)
    # --- THIS COMMIT CAN FAIL IF SCHEMA IS WRONG ---
    try:
        db_session.commit()
        print(f"Added test consignment: {cons_id}")
    except Exception as e:
        print(f"!!! Error during commit in test_manager_assign_consignment_success (Consignment): {e} !!!")
        pytest.fail(f"Commit failed, likely schema issue: {e}")

    assign_data = {'consignment_id': cons.id, 'truck_id': truck.id}
    print(f"Attempting assignment: {assign_data}")
    # --- THIS POST REQUEST CAN FAIL IF SCHEMA IS WRONG IN ROUTE ---
    response = logged_in_manager.post('/consignments/assign', json=assign_data)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Data: {response.data.decode(errors='ignore')}")

    assert response.status_code == 200 # Expect OK status from your route

    db_session.refresh(cons)
    db_session.refresh(truck)
    assert cons.status == 'Dispatched'
    assert truck.status == 'In-Transit'
    assignment_link = db_session.query(ConsignmentTruck).filter_by(consignment_id=cons.id, truck_id=truck.id).first()
    assert assignment_link is not None
    print("Verified DB changes after successful assignment.")

def test_manager_assign_consignment_exceeds_capacity(logged_in_manager, db_session, ensure_truck_citya1_exists):
    """Test assigning consignment fails if truck capacity (500) is exceeded."""
    truck = ensure_truck_citya1_exists # Truck with capacity 500
    cons_id_1 = 'cons-cap-test-1'
    cons_id_2 = 'cons-cap-test-2'
    print(f"\n--- Test: test_manager_assign_consignment_exceeds_capacity ---")
    print(f"Using truck: {truck.id} (Capacity: {truck.capacity}) in branch {truck.branch_id}")

    cons1 = Consignment(id=cons_id_1, volume=300, destination='D', sender_name='S1', sender_address='SA1', receiver_name='R1', receiver_address='RA1', charge=1, branch_id=truck.branch_id, status='Pending')
    cons2 = Consignment(id=cons_id_2, volume=250, destination='D', sender_name='S2', sender_address='SA2', receiver_name='R2', receiver_address='RA2', charge=1, branch_id=truck.branch_id, status='Pending')
    db_session.add_all([cons1, cons2])
    # --- THIS COMMIT CAN FAIL IF SCHEMA IS WRONG ---
    try:
        db_session.commit()
        print(f"Added test consignments: {cons_id_1}, {cons_id_2}")
    except Exception as e:
         print(f"!!! Error during commit in test_manager_assign_consignment_exceeds_capacity: {e} !!!")
         pytest.fail(f"Commit failed, likely schema issue: {e}")


    # Assign the first one (should succeed)
    assign_data1 = {'consignment_id': cons1.id, 'truck_id': truck.id}
    print(f"Attempting assignment 1 (should succeed): {assign_data1}")
    response1 = logged_in_manager.post('/consignments/assign', json=assign_data1)
    print(f"Response 1 Status Code: {response1.status_code}")
    assert response1.status_code == 200

    # Attempt to assign the second one (should fail)
    assign_data2 = {'consignment_id': cons2.id, 'truck_id': truck.id}
    print(f"Attempting assignment 2 (should fail - exceed capacity): {assign_data2}")
    response2 = logged_in_manager.post('/consignments/assign', json=assign_data2)
    print(f"Response 2 Status Code: {response2.status_code}")
    print(f"Response 2 Data: {response2.data.decode(errors='ignore')}")

    assert response2.status_code == 400 # Expect failure due to capacity
    assert b"exceed truck capacity" in response2.data

    db_session.refresh(cons2)
    assert cons2.status == 'Pending'
    print("Verified second assignment failed and consignment status remains Pending.")