from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, LoginSerializer, RefreshSerializer
from .serializers import LogoutSerializer
from rest_framework.permissions import IsAuthenticated


# Registration API
class RegisterView(APIView):

    def post(self, request):

        # Pass the incoming request data to the serializer
        serializer = RegisterSerializer(data=request.data)

        # Check whether the submitted data is valid
        if serializer.is_valid():

            # Save the new user in the database
            user = serializer.save()

            # Return a successful response
            return Response(
                {
                    "message": "User registered successfully",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "phone": user.phone,
                        "role": user.role,
                        "tier": user.tier
                    }
                },
                status=status.HTTP_201_CREATED
            )

        # Return validation errors if data is invalid
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



class LoginView(APIView):

    def post(self, request):

        # Pass login data to the serializer
        serializer = LoginSerializer(data=request.data)

        # Validate email and password
        if serializer.is_valid():

            # Get the authenticated user from serializer
            user = serializer.validated_data["user"]

            # Generate a refresh token for this user
            refresh = RefreshToken.for_user(user)

            # Add custom information to the JWT token
            refresh["role"] = user.role
            refresh["tier"] = user.tier

            # Generate access token
            access = refresh.access_token

            return Response(
                {
                    "message": "Login successful",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role,
                        "tier": user.tier
                    },
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(access)
                    }
                },
                status=status.HTTP_200_OK
            )

        # Return validation errors
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class RefreshView(APIView):

    def post(self, request):

        # Pass the refresh token to the serializer
        serializer = RefreshSerializer(data=request.data)

        # Validate the refresh token
        if serializer.is_valid():

            # Get the newly generated tokens
            return Response(
                {
                    "message": "Token refreshed successfully",
                    "tokens": serializer.validated_data
                },
                status=status.HTTP_200_OK
            )

        # Return an error if the refresh token is invalid
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class LogoutView(APIView):

    def post(self, request):

        # Receive the refresh token from the request
        serializer = LogoutSerializer(data=request.data)

        if serializer.is_valid():

            # Get the validated refresh token
            refresh_token = serializer.validated_data["token"]

            # Blacklist the refresh token
            refresh_token.blacklist()

            return Response(
                {"message": "Logout successful"},
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class MeView(APIView):

    # Only authenticated users can access this API , you need to provide the jwt access token.
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Get the currently logged-in user
        user = request.user

        return Response({
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "tier": user.tier
        }, status=status.HTTP_200_OK)