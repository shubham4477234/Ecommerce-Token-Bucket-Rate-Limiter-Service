from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from customer.services import merge_guest_cart, preserve_cart_in_session
from .serializers import RegisterSerializer, LoginSerializer, RefreshSerializer
from .serializers import LogoutSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rate_limiter.throttles import TokenBucketThrottle

# Registration API
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [TokenBucketThrottle]
    throttle_scope = "register"
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
    permission_classes = [AllowAny]
    throttle_classes = [TokenBucketThrottle]
    throttle_scope = "login"
    def post(self, request):

        # Pass login data to the serializer
        serializer = LoginSerializer(data=request.data)

        # Validate email and password
        if serializer.is_valid():

            # Get the authenticated user
            user = serializer.validated_data["user"]

            # Merge guest cart into the customer's database cart
            cart_result = merge_guest_cart(request, user)

            # Generate refresh token
            refresh = RefreshToken.for_user(user)

            # Add custom information to JWT
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
                    },
                    "cart": cart_result
                },
                status=status.HTTP_200_OK
            )

        # Return validation errors
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [TokenBucketThrottle]
    throttle_scope = "refresh"
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
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # Validate the refresh token
        serializer = LogoutSerializer(data=request.data)

        if serializer.is_valid():

            # Copy database cart into Django session
            preserve_cart_in_session(request, request.user)

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