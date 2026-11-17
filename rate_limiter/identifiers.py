
from django.conf import settings
from rest_framework.exceptions import APIException


class ClientIdentificationError(APIException):
    status_code = 503
    default_detail = "Unable to identify the request client safely."
    default_code = "client_identification_failed"


def get_client_ip(request):
    """
    Identify the client IP.

    Only trust X-Forwarded-For when the application is behind
    a correctly configured trusted proxy.
    """

    trusted_proxy_count = getattr(
        settings,
        "RATE_LIMIT_TRUSTED_PROXY_COUNT",
        0
    )

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if trusted_proxy_count > 0:

        if not forwarded_for:
            raise ClientIdentificationError()

        ip_addresses = [
            ip.strip()
            for ip in forwarded_for.split(",")
            if ip.strip()
        ]

        if len(ip_addresses) <= trusted_proxy_count:
            raise ClientIdentificationError()

        # Select the client IP immediately before the trusted proxies
        client_ip = ip_addresses[-(trusted_proxy_count + 1)]

    else:
        # Direct connection: use the peer address
        client_ip = request.META.get("REMOTE_ADDR")

    if not client_ip:
        raise ClientIdentificationError()

    return client_ip


def get_client_identifier(request):
    """
    Generate a unique identifier for the request client.
    """

    user = request.user

    if user and user.is_authenticated:

        return f"user:{user.pk}"

    client_ip = get_client_ip(request)

    return f"ip:{client_ip}"
