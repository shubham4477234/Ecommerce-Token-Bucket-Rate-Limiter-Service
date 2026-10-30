from rest_framework import serializers
from .models import User
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers

class RegisterSerializer(serializers.ModelSerializer):

    # User must enter the password twice
    confirm_password = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = User

        # Fields accepted during registration
        fields = [
            "email",
            "phone",
            "password",
            "confirm_password",
        ]

        # Password should never be returned in API responses
        extra_kwargs = {
            "password": {
                "write_only": True
            }
        }

    # Check whether both passwords match
    def validate(self, data):

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )

        return data

    # Create a new user
    def create(self, validated_data):

        # Remove confirm_password because it is not a User model field
        validated_data.pop("confirm_password")

        # Create user using our custom manager
        user = User.objects.create_user(
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
        )

        return user



class LoginSerializer(serializers.Serializer):

    # Fields received from the login request
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    # Validate the login credentials
    def validate(self, data):

        # Get the email and password from request data
        email = data.get("email")
        password = data.get("password")

        # Get our custom User model
        User = get_user_model()

        # Find the user using email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid email or password"
            )

        # Check whether the password is correct
        if not user.check_password(password):
            raise serializers.ValidationError(
                "Invalid email or password"
            )

        # Check whether the account is active
        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive"
            )

        # Store the user object for later use in the view
        data["user"] = user

        return data


class RefreshSerializer(TokenRefreshSerializer):
    pass


class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()

    def validate(self, data):

        try:
            # Convert the provided string into a RefreshToken object
            token = RefreshToken(data["refresh"])

            # Store the token object for the next step
            data["token"] = token

            return data

        except Exception:
            raise serializers.ValidationError(
                {"refresh": "Invalid or expired refresh token"}
            )