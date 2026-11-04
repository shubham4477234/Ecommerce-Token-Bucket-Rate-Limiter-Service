from rest_framework.permissions import BasePermission


# Allow access only to sellers
class IsSeller(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "seller"
        )


class IsAdmin(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )