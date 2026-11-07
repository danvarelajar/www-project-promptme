"""Mica Logistics: the fictional company every challenge is set in.

A mid-sized freight and warehousing firm. Keep details consistent across
challenges by using these constants. The name was checked against real
companies: none trades as exactly "Mica Logistics" (closest: small carriers
such as Mica Transportation and Mika Logistics, different firms). The domain
uses .example, which is reserved and never resolves.
"""

NAME = "Mica Logistics"
SHORT = "Mica"
DOMAIN = "mica-logistics.example"          # .example: reserved, never resolves
TAGLINE = "Freight and warehousing across Europe"
HQ = "Rotterdam"
WAREHOUSES = ["Rotterdam", "Antwerp", "Hamburg", "Lyon", "Gdansk"]


def email(user):
    return f"{user}@{DOMAIN}"
