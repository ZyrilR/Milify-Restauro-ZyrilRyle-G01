# Milify

Milify is a Django-based project management system for students and small development teams. It helps owners organize projects and share them with members.

## Core feature: Project Management

Project owners can create, view, update, and delete their own projects. They can invite registered Milify members by username or generate a six-character invite code to share. Invitations remain pending until the invited member accepts or declines; accepting creates a project membership. Members can review pending invitations and see projects they have joined on their dashboard.

Invite codes currently have no attempt limit. Add rate limiting or stronger codes before exposing the application publicly.

## Tech stack

- Python and Django (backend and server-rendered templates)
- PostgreSQL (including Supabase PostgreSQL); SQLite is used when PostgreSQL settings are not provided
- Django authentication

## Setup

1. Install Python and create/activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install project dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Configure PostgreSQL/Supabase (optional for local development; without these settings, Django uses SQLite). Create `.env.local` in the repository root:

   ```dotenv
   POSTGRES_DB=postgres
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_database_password
   POSTGRES_HOST=your_database_host
   POSTGRES_PORT=5432
   ```

   The same settings can be copied from `.env.example` and filled with your own database credentials. Keep `.env.local` private; do not commit credentials.

4. Apply database migrations and start the development server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

   Visit <http://127.0.0.1:8000/> to register or log in. Django admin is at <http://127.0.0.1:8000/admin/>; create an administrator account with `python manage.py createsuperuser` if needed.

## Tests

```powershell
python manage.py test
```
