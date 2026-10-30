
from django.db import connections
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    try:
        # Close any existing connection.
        connections["default"].close()

        # Attempt a fresh database connection.
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            "status": "ok",
            "database": "connected",
        }, status=200)

    except (DatabaseError, OSError):
        connections["default"].close()

        return JsonResponse({
            "status": "error",
            "database": "disconnected",
        }, status=503)
