
# Import Django's base user manager
from django.contrib.auth.base_user import BaseUserManager


# Our custom manager for creating users
class UserManager(BaseUserManager):

    # Function to create a normal user
    def create_user(self, email, phone, password=None):

        # Check whether email is provided
        if not email:
            raise ValueError("Email is required")

        # Check whether phone number is provided
        if not phone:
            raise ValueError("Phone number is required")

        # Convert email domain to lowercase
        email = self.normalize_email(email)

        # Create a user object
        user = self.model(
            email=email,
            phone=phone
        )

        # Hash the password before saving it
        user.set_password(password)

        # Save the user in the database
        user.save(using=self._db)

        return user

    # Function to create an admin user
    def create_superuser(self, email, phone, password=None):

        # Create the user using our create_user function
        user = self.create_user(
            email=email,
            phone=phone,
            password=password
        )

        # Give the user admin permissions
        user.role = "admin"
        user.is_staff = True
        user.is_superuser = True

        # Save the updated user
        user.save(using=self._db)

        return user
