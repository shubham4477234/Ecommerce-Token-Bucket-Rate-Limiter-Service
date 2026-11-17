from rest_framework.exceptions import APIException


class RateLimiterUnavailableAPIException(APIException):

    status_code = 503
    default_detail = (
        "Rate limiting service is temporarily unavailable. "
        "Please try again later."
    )
    default_code = "rate_limiter_unavailable"