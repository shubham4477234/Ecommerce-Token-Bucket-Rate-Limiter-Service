
from django.core.cache import cache


# Customer product listing cache version
CUSTOMER_PRODUCT_LIST_VERSION_KEY = (
    "customer:products:list:version"
)


def increment_cache_version(key):
    """
    Create a cache version if it does not exist.
    Otherwise, increment its existing version.
    """

    if not cache.add(key, 1, timeout=None):
        cache.incr(key)


def invalidate_customer_product_listing_cache():
    """
    Invalidate all cached customer product listing responses.

    Incrementing the version makes previous listing cache
    keys unreachable.
    """

    increment_cache_version(
        CUSTOMER_PRODUCT_LIST_VERSION_KEY
    )


def invalidate_customer_product_detail_cache(seller_product_id):
    """
    Invalidate the detail cache for one seller product listing.

    Each listing has its own cache version.
    """

    detail_version_key = (
        f"customer:products:detail:version:{seller_product_id}"
    )

    increment_cache_version(detail_version_key)


def invalidate_customer_product_cache(seller_product_id=None):
    """
    Invalidate customer product caches.

    Always invalidates product listing responses.

    If seller_product_id is supplied, also invalidates
    that specific product detail response.
    """

    invalidate_customer_product_listing_cache()

    if seller_product_id is not None:
        invalidate_customer_product_detail_cache(
            seller_product_id
        )



def invalidate_customer_category_cache():
    cache.delete("customer:categories:tree")

def invalidate_customer_cart_cache(customer_id):
    cache.delete(f"customer:cart:{customer_id}")