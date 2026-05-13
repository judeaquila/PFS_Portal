# Django Scalable RBAC Boilerplate

A production-ready Django starter template featuring Custom User Models and Role-Based Access Control (RBAC).

## 🚀 Features
- **Custom User Model:** Using Email as the primary identifier instead of Username.
- **Role-Based Access:** Built-in roles (Super Admin, Supervisor, Consultant, User).
- **Custom Auth Backend:** Supports authentication via Email.
- **Access Control:** Includes `@role_required` decorators and role-based redirection logic.
- **Scalable Architecture:** Clean separation of concerns with `accounts`, `dashboard`, and `common` apps.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone (https://github.com/judeaquila/rbac_django.git)
   cd rbac_django

2. **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt

4. **Run Migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate

5. **Create a Superuser:**
    ```bash
    python manage.py createsuperuser


## 🔑 Role Management
Roles are defined in `accounts/models.py`. When creating users via the shell, ensure you use the `UserRole` constants:
    ```bash
    from accounts.models import User, UserRole
    User.objects.create_user(email="user@example.com", password="password", role=UserRole.SUPERVISOR)
