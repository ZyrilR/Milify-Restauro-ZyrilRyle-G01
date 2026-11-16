# Milify

Milify is a Django-based project management system for students and small development teams. It helps organize projects, members, tasks, milestones, and progress.

## Tech stack

- Python and Django (backend and server-rendered templates)
- PostgreSQL or Supabase PostgreSQL
- Django authentication

## Run locally

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create `.env.local` in the repository root with your PostgreSQL connection settings:

   ```dotenv
   POSTGRES_DB=your_database
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=your_host
   POSTGRES_PORT=5432
   ```

   Keep credentials private. The app expects PostgreSQL; configure these values before running it.

4. Apply migrations and start the development server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

   Visit <http://127.0.0.1:8000/>. Django admin is at <http://127.0.0.1:8000/admin/>. Create an admin account with `python manage.py createsuperuser`.

## Tests

```powershell
python manage.py test
```
