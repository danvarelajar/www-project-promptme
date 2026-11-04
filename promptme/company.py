"""Kestrelline Logistics: the fictional company every challenge is set in.

A mid-sized freight and warehousing firm. Keep details consistent across
challenges by using these constants. The name was checked against real
companies (closest: Kestrel Liner Agencies Ltd, a different firm).
"""

NAME = "Kestrelline Logistics"
SHORT = "Kestrelline"
DOMAIN = "kestrelline.example"          # .example: reserved, never resolves
TAGLINE = "Freight and warehousing across Europe"
HQ = "Rotterdam"
WAREHOUSES = ["Rotterdam", "Antwerp", "Hamburg", "Lyon", "Gdansk"]


def email(user):
    return f"{user}@{DOMAIN}"
