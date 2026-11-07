# Task 3 -- Student Management System

## Project Overview

This project is a Flask-based Student Management System. It allows
registered users to log in and view student records. Administrators have
additional permissions to create, update, and delete student records,
and to manage user roles.

The application uses:

-   **Python** and **Flask** for the backend.
-   **SQLite** for storing users and student records.
-   **HTML and CSS** for the web interface.
-   **Flask sessions** for user authentication.
-   **Werkzeug password hashing** for securely storing passwords.
-   **Postman** for testing the REST API.

## Main Features

-   User registration and login.
-   Password hashing rather than storing plain-text passwords.
-   Session-based authentication for protected pages.
-   Role-based access control for normal users and administrators.
-   Student record management (CRUD).
-   JSON API endpoints for student records.
-   Admin functions for managing users and roles.

## CRUD Flow

CRUD stands for **Create, Read, Update, and Delete**.

### 1. Create -- Add a student

1.  An administrator logs in.
2.  The administrator opens the **Add Student** page or sends a `POST`
    request to `/api/students`.
3.  The application checks that the user is authenticated and has the
    administrator role.
4.  The submitted student details are validated.
5.  If the details are valid, the application inserts the new student
    record into the SQLite `students` table.
6.  The application returns a success response.

Example API request:

-   Method: `POST`
-   URL: `/api/students`
-   Body: raw JSON

``` json
{
  "name": "Postman Test Student",
  "email": "student@example.com",
  "course": "Python Full Stack"
}
```

Use the field names expected by the application's API if they differ
from this example.

### 2. Read -- View student records

1.  The user logs in.
2.  The user opens the **View Students** page or sends a `GET` request
    to `/api/students`.
3.  The application checks authentication.
4.  The application reads student records from SQLite.
5.  The records are returned as JSON by the API or displayed in the web
    page.

To retrieve one student, send:

-   Method: `GET`
-   URL: `/api/students/<id>`

Replace `<id>` with the student's numeric database ID.

### 3. Update -- Edit a student

1.  An administrator selects a student and opens the edit page, or sends
    a `PUT` request to `/api/students/<id>`.
2.  The application checks authentication and administrator permissions.
3.  The application validates the new values.
4.  The matching student record is updated in SQLite.
5.  The application returns a success or error response.

Example API request:

-   Method: `PUT`
-   URL: `/api/students/6`
-   Body: raw JSON

``` json
{
  "course": "Cybersecurity"
}
```

The example ID is illustrative. Use an ID that exists in your database
and the fields supported by your API.

### 4. Delete -- Remove a student

1.  An administrator selects the student to remove or sends a `DELETE`
    request to `/api/students/<id>`.
2.  The application checks authentication and administrator permissions.
3.  The application deletes the matching record from SQLite.
4.  The application returns a success response. A later request for that
    deleted ID should report that the student was not found.

Example:

-   Method: `DELETE`
-   URL: `/api/students/6`

The example ID is illustrative. Use an existing student ID.

## Authentication and Authorization Flow

1.  A user registers through the registration page or
    `POST /api/auth/register`.
2.  The application validates the registration details and stores the
    account with a hashed password.
3.  The user logs in through the login page or `POST /api/auth/login`.
4.  After successful login, the application creates an authenticated
    session.
5.  Protected routes check whether a session exists.
6.  Administrator-only operations also check the user's role.

Typical API errors include:

-   **401 Unauthorized** -- authentication is required or the session is
    missing/invalid.
-   **403 Forbidden** -- the user is authenticated but does not have
    administrator permission.
-   **404 Not Found** -- the requested student or endpoint does not
    exist.

## API Endpoint Reference

  Method   Endpoint               Purpose
  -------- ---------------------- --------------------------
  POST     `/api/auth/register`   Register a user
  POST     `/api/auth/login`      Log in
  POST     `/api/auth/logout`     Log out
  GET      `/api/students`        List student records
  GET      `/api/students/<id>`   Retrieve one student
  POST     `/api/students`        Create a student (admin)
  PUT      `/api/students/<id>`   Update a student (admin)
  DELETE   `/api/students/<id>`   Delete a student (admin)

The web application also provides pages for the dashboard, student
listing, adding/editing students, and administrator user management.

## Database

The application uses SQLite. The database file is initialized by the
application's database initialization code. It contains user account
data and student records.

-   The `users` table stores account details, including the user's role
    and hashed password.
-   The `students` table stores student information.

The database file is local application data. It should not be committed
to a public Git repository. Keep secrets such as the Flask secret key
out of source control.

## How to Run Locally (Windows)

1.  Open PowerShell.
2.  Change to the project directory:

``` powershell
cd "C:\Users\Zephy\Downloads\python-fullstack-task3,4"
```

3.  Install the dependencies:

``` powershell
py -m pip install -r requirements.txt
```

4.  Start the Flask application:

``` powershell
py app.py
```

5.  Open the local address printed by Flask in your browser. In the
    development setup, this is usually:

``` text
http://127.0.0.1:5000
```

Use the administrator account configured for your own project to test
administrator-only functions. Do not put real passwords in this README.

## Testing with Postman

1.  Start the Flask application.
2.  Open Postman and create requests using the endpoint reference above.
3.  Register a test user and log in.
4.  For protected API requests, send the authentication session/cookie
    established by the login request. If using Postman's cookie manager,
    keep the cookie for `127.0.0.1` when making subsequent requests.
5.  Test a normal user against an administrator-only endpoint and
    confirm that access is denied.
6.  Log in as an administrator and test `POST`, `GET`, `PUT`, and
    `DELETE`.
7.  Test invalid IDs and unauthenticated requests to confirm the error
    responses.

## Security and Submission Notes

-   Passwords should be stored as hashes, not plain text.
-   Keep `SECRET_KEY` and other credentials out of GitHub.
-   Do not upload the live `database.db` or private database backups to
    a public repository.
-   Include screenshots of the working application and Postman tests in
    the submission if required.
-   Confirm that the route names and JSON field names in this README
    match the final version of your code before submitting.
