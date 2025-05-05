# tests/test_auth.py

import pytest
from flask import session

# Assuming models are accessible via app import if needed, but often not directly needed here
# from app import User

def test_login_page_loads(client):
    """Test that the login page loads correctly."""
    print("\n--- Test: test_login_page_loads ---")
    response = client.get('/login')
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    assert b"TCCS Login" in response.data # Check for title or heading

def test_manager_login_success(client, ensure_manager_exists): # Uses ensure fixture
    """Test successful login for a manager."""
    manager = ensure_manager_exists
    print(f"\n--- Test: test_manager_login_success ---")
    print(f"Attempting login for user: {manager.username} (ID: {manager.id})")
    response = client.post('/login', data={
        'username': 'manager1',
        'password': 'managerpass'
    }, follow_redirects=True) # Follow redirect to dashboard

    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    assert b'Manager Dashboard' in response.data # Check manager dashboard content
    # Check session
    with client.session_transaction() as sess:
       assert 'user_id' in sess
       assert sess['user_id'] == manager.id
       assert sess.get('user_role') == 'Manager'

def test_employee_login_success(client, ensure_employee_exists): # Uses ensure fixture
    """Test successful login for an employee."""
    employee = ensure_employee_exists
    print(f"\n--- Test: test_employee_login_success ---")
    print(f"Attempting login for user: {employee.username} (ID: {employee.id}, Branch: {employee.branch_id})")
    response = client.post('/login', data={
        'username': 'employee1',
        'password': 'employeepass'
    }, follow_redirects=True)

    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    assert b'Employee Dashboard' in response.data # Check employee dashboard content
     # Check session
    with client.session_transaction() as sess:
       assert 'user_id' in sess
       assert sess['user_id'] == employee.id
       assert sess.get('user_role') == 'Employee'

def test_login_invalid_password(client, ensure_manager_exists):
    """Test login fails with incorrect password."""
    print("\n--- Test: test_login_invalid_password ---")
    response = client.post('/login', data={
        'username': 'manager1',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200 # Still 200 because it renders the login page again
    assert b"Invalid credentials" in response.data
    # Check session is empty
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_login_invalid_username(client):
    """Test login fails with non-existent username."""
    print("\n--- Test: test_login_invalid_username ---")
    response = client.post('/login', data={
        'username': 'nousername',
        'password': 'somepassword'
    }, follow_redirects=True)
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_logout(logged_in_manager): # Uses logged_in fixture
    """Test logging out clears the session."""
    print("\n--- Test: test_logout ---")
    # logged_in_manager fixture ensures client is already logged in
    with logged_in_manager.session_transaction() as sess:
        assert 'user_id' in sess # Verify user IS logged in initially

    print("Making GET request to /logout")
    response = logged_in_manager.get('/logout', follow_redirects=True)
    print(f"Response Status Code: {response.status_code}")

    assert response.status_code == 200
    assert b'TCCS Login' in response.data # Should redirect to login page

    # Verify session is now empty
    with logged_in_manager.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'user_role' not in sess
    print("Verified session is empty after logout.")


def test_access_dashboard_unauthenticated(client):
    """Test accessing dashboard requires login."""
    print("\n--- Test: test_access_dashboard_unauthenticated ---")
    response = client.get('/dashboard', follow_redirects=True)
    print(f"Response Status Code: {response.status_code}")
    assert response.status_code == 200 # Redirects to login
    assert b'TCCS Login' in response.data # Should show login page
    assert request.path == '/login' # Check final URL path after redirect