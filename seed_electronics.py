"""
Idempotent demo-data seeder for LimitGuard electronics catalogue.

Run from the project root:
    python manage.py shell < seed_electronics.py

Creates 5 demo sellers, 50 electronics products by default, seller listings,
2 product lines per product, attributes and attribute values.
Does not delete existing data or create image files.
"""

import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from seller.models import (
    SellerProfile, Category, ProductType, Attribute, AttributeValue,
    ProductTypeAttribute, Product, SellerProduct, ProductAttributeValue,
    ProductLine, ProductLineAttributeValue,
)

User = get_user_model()
rng = random.Random(42)
PASSWORD = "DemoSeller@123"

SELLER_DATA = [
    ("demo.seller1@limitguard.test", "+919800000101", "TechNova Electronics", "technova-electronics"),
    ("demo.seller2@limitguard.test", "+919800000102", "Gadget Galaxy", "gadget-galaxy"),
    ("demo.seller3@limitguard.test", "+919800000103", "NextGen Digital", "nextgen-digital"),
    ("demo.seller4@limitguard.test", "+919800000104", "Circuit Central", "circuit-central"),
    ("demo.seller5@limitguard.test", "+919800000105", "Digital Depot", "digital-depot"),
]

# Five models per type; ten types = fifty products.
FAMILIES = [
    ("Smartphone", "Mobile Phones", ["Samsung Galaxy S25", "Apple iPhone 16", "OnePlus 12R", "Xiaomi 14", "Motorola Edge 50"], 35000, ["128 GB", "256 GB"], ["8 GB", "12 GB"]),
    ("Laptop", "Laptops", ["Dell Inspiron 14", "HP Pavilion 15", "Lenovo IdeaPad Slim 5", "ASUS Vivobook 16", "Acer Swift Go 14"], 56000, ["512 GB SSD", "1 TB SSD"], ["8 GB", "16 GB"]),
    ("Tablet", "Tablets", ["Apple iPad Air", "Samsung Galaxy Tab S10", "Xiaomi Pad 6", "OnePlus Pad 2", "Lenovo Tab P12"], 25000, ["128 GB", "256 GB"], ["6 GB", "8 GB"]),
    ("Smartwatch", "Wearables", ["Apple Watch Series 10", "Samsung Galaxy Watch 7", "Noise ColorFit Pro 5", "Amazfit GTR Mini", "Garmin Forerunner 165"], 7000, ["16 GB", "32 GB"], ["1 GB", "2 GB"]),
    ("Headphones", "Audio", ["Sony WH-1000XM5", "Bose QuietComfort", "JBL Tune 770NC", "Sennheiser Accentum", "boAt Rockerz 550"], 4000, ["Standard"], ["Standard"]),
    ("Television", "Televisions", ["Samsung Crystal UHD", "LG OLED C4", "Sony Bravia 3", "TCL QLED Pro", "Hisense U7N"], 28000, ["Standard"], ["Standard"]),
    ("Camera", "Cameras", ["Canon EOS R50", "Nikon Z50", "Sony Alpha A6400", "Fujifilm X-S20", "Panasonic Lumix G7"], 46000, ["64 GB", "128 GB"], ["Standard"]),
    ("Gaming Console", "Gaming", ["Sony PlayStation 5 Slim", "Microsoft Xbox Series X", "Nintendo Switch OLED", "Sony PlayStation 5 Pro", "Microsoft Xbox Series S"], 33000, ["512 GB", "1 TB"], ["Standard"]),
    ("Router", "Networking", ["TP-Link Archer AX55", "D-Link DIR-X1560", "ASUS RT-AX58U", "Netgear RAX10", "Xiaomi AX3000"], 2500, ["Standard"], ["Standard"]),
    ("Monitor", "Computer Monitors", ["LG UltraGear 27", "Samsung Odyssey G5", "AOC Gaming 24G2", "Acer Nitro VG271", "Dell UltraSharp 27"], 12000, ["Standard"], ["Standard"]),
]

COLORS = ["Black", "Silver", "Blue", "White", "Graphite"]
COMMON_VALUES = {
    "Warranty": ["1 Year", "2 Years"],
    "Connectivity": ["Bluetooth", "Wi-Fi", "Wi-Fi + Bluetooth", "5G", "Wi-Fi 6", "HDMI", "USB-C"],
    "Screen Size": ["6.1 inch", "6.7 inch", "10.9 inch", "14 inch", "15.6 inch", "27 inch", "55 inch"],
    "Processor": ["Intel Core i5", "Intel Core i7", "AMD Ryzen 5", "Apple M-series"],
    "Operating System": ["Android", "iOS", "Windows 11", "Google TV", "Tizen", "webOS"],
    "Battery Capacity": ["300 mAh", "400 mAh", "5000 mAh"],
    "Refresh Rate": ["60 Hz", "75 Hz", "120 Hz", "144 Hz", "165 Hz"],
}

TYPE_ATTRIBUTES = {
    "Smartphone": ["Brand", "Model Number", "Warranty", "Color", "Storage", "RAM", "Connectivity", "Battery Capacity"],
    "Laptop": ["Brand", "Model Number", "Warranty", "Color", "Storage", "RAM", "Processor", "Screen Size", "Operating System"],
    "Tablet": ["Brand", "Model Number", "Warranty", "Color", "Storage", "RAM", "Connectivity", "Screen Size"],
    "Smartwatch": ["Brand", "Model Number", "Warranty", "Color", "Connectivity", "Battery Capacity"],
    "Headphones": ["Brand", "Model Number", "Warranty", "Color", "Connectivity"],
    "Television": ["Brand", "Model Number", "Warranty", "Color", "Screen Size", "Connectivity", "Operating System"],
    "Camera": ["Brand", "Model Number", "Warranty", "Color", "Storage", "Connectivity"],
    "Gaming Console": ["Brand", "Model Number", "Warranty", "Color", "Storage", "Connectivity"],
    "Router": ["Brand", "Model Number", "Warranty", "Color", "Connectivity"],
    "Monitor": ["Brand", "Model Number", "Warranty", "Color", "Screen Size", "Refresh Rate", "Connectivity"],
}

def attr_value(attribute, value):
    obj, _ = AttributeValue.objects.get_or_create(attribute=attribute, value=value)
    return obj

@transaction.atomic
def seed():
    sellers = []
    for email, phone, store, store_slug in SELLER_DATA:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"phone": phone, "role": "seller", "is_active": True},
        )
        if created:
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
        elif user.role != "seller":
            raise ValueError(f"{email} exists but is not a seller.")
        profile, _ = SellerProfile.objects.get_or_create(
            user=user,
            defaults={
                "store_name": store,
                "store_slug": store_slug,
                "description": f"Demo electronics seller: {store}",
                "business_email": email,
                "business_phone": phone,
                "address": "Pune, Maharashtra, India",
                "verification_status": "verified",
                "is_active": True,
            },
        )
        sellers.append(profile)

    root, _ = Category.objects.get_or_create(
        slug="electronics",
        defaults={"name": "Electronics", "description": "Electronic products", "is_active": True},
    )

    attributes = {}
    all_attribute_names = sorted({a for names in TYPE_ATTRIBUTES.values() for a in names})
    for name in all_attribute_names:
        attributes[name], _ = Attribute.objects.get_or_create(
            name=name, defaults={"description": f"{name} product specification", "is_active": True}
        )

    # Set up attribute values and product-type/attribute relationships.
    type_objects = {}
    category_objects = {}
    for type_name, category_name, names, base_price, storage_options, ram_options in FAMILIES:
        category_slug = slugify(category_name)
        category_objects[type_name], _ = Category.objects.get_or_create(
            slug=category_slug,
            defaults={
                "name": category_name, "description": f"{category_name} electronics",
                "is_active": True, "parent": root,
            },
        )
        type_objects[type_name], _ = ProductType.objects.get_or_create(
            name=type_name, defaults={"is_active": True}
        )
        ptype = type_objects[type_name]
        if not ptype.is_active:
            ptype.is_active = True
            ptype.save(update_fields=["is_active"])

        for name in TYPE_ATTRIBUTES[type_name]:
            ProductTypeAttribute.objects.get_or_create(
                product_type=ptype, attribute=attributes[name],
                defaults={"is_required": name in ("Brand", "Model Number")},
            )

        family_values = {
            "Brand": [n.split()[0] for n in names],
            "Model Number": names,
            "Color": COLORS,
            "Storage": storage_options,
            "RAM": ram_options,
        }
        for attr_name in TYPE_ATTRIBUTES[type_name]:
            values = set(COMMON_VALUES.get(attr_name, []))
            values.update(family_values.get(attr_name, []))
            for value in values:
                attr_value(attributes[attr_name], value)

    # Create products, seller listings and variants.
    products_done = 0
    lines_done = 0
    for family_index, family in enumerate(FAMILIES):
        type_name, category_name, names, base_price, storage_options, ram_options = family
        ptype = type_objects[type_name]
        category = category_objects[type_name]
        for model_index, product_name in enumerate(names):
            if products_done >= 50:
                break
            slug = slugify(f"{type_name}-{product_name}")
            pid = f"LG-{family_index + 1:02d}-{model_index + 1:03d}"
            product, _ = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": product_name,
                    "pid": pid,
                    "description": f"{product_name}: demo {type_name.lower()} product for the LimitGuard catalogue.",
                    "is_digital": False,
                    "category": category,
                    "product_type": ptype,
                    "is_active": True,
                },
            )

            brand = product_name.split()[0]
            for attr_name, value in (("Brand", brand), ("Model Number", product_name)):
                pav = attr_value(attributes[attr_name], value)
                ProductAttributeValue.objects.get_or_create(product=product, attribute_value=pav)

            seller = sellers[products_done % len(sellers)]
            listing, _ = SellerProduct.objects.get_or_create(
                seller=seller, product=product,
                defaults={"seller_product_name": product_name, "is_active": True},
            )

            for variant_no in range(2):
                sku = f"{pid}-V{variant_no + 1}"
                price = (Decimal(base_price) * Decimal(str(rng.uniform(0.92, 1.12)))).quantize(Decimal("0.01"))
                line, _ = ProductLine.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "seller_product": listing, "price": price,
                        "stock_qty": rng.randint(5, 80),
                        "weight": Decimal(str(rng.uniform(0.1, 8.0))).quantize(Decimal("0.001")),
                        "is_active": True,
                    },
                )

                variant_values = {
                    "Color": COLORS[variant_no],
                    "Warranty": "1 Year",
                }
                if "Storage" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Storage"] = storage_options[variant_no % len(storage_options)]
                if "RAM" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["RAM"] = ram_options[variant_no % len(ram_options)]
                if "Connectivity" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Connectivity"] = "Wi-Fi + Bluetooth"
                if "Screen Size" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Screen Size"] = "15.6 inch" if type_name == "Laptop" else (
                        "55 inch" if type_name == "Television" else "27 inch" if type_name == "Monitor" else "10.9 inch"
                    )
                if "Processor" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Processor"] = "Intel Core i5"
                if "Operating System" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Operating System"] = "Windows 11" if type_name == "Laptop" else "Android"
                if "Refresh Rate" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Refresh Rate"] = "144 Hz"
                if "Battery Capacity" in TYPE_ATTRIBUTES[type_name]:
                    variant_values["Battery Capacity"] = "5000 mAh"

                for attr_name, value in variant_values.items():
                    av = attr_value(attributes[attr_name], value)
                    ProductLineAttributeValue.objects.get_or_create(
                        product_line=line, attribute_value=av
                    )
                lines_done += 1

            products_done += 1

    print("LimitGuard electronics seed completed.")
    print(f"Demo sellers: {len(sellers)}")
    print(f"Products: {products_done}")
    print(f"Seller listings: {products_done}")
    print(f"Product lines: {lines_done}")
    print(f"Demo seller password: {PASSWORD}")
    print("No existing records were deleted. ProductImage records were not created.")

seed()
