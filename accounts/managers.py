from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    # Create a normal customer or seller
    def create_user(self, email, phone, password=None, role="customer"):

        if not email:
            raise ValueError("Email is required")

        if not phone:
            raise ValueError("Phone number is required")

        # Prevent public user creation with admin role
        if role not in ["customer", "seller"]:
            raise ValueError("Role must be customer or seller")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            phone=phone,
            role=role
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    # Create an admin account
    def create_superuser(self, email, phone, password=None):

        user = self.create_user(
            email=email,
            phone=phone,
            password=password,
            role="customer"
        )

        user.role = "admin"
        user.is_staff = True
        user.is_superuser = True

        user.save(using=self._db)

        return user