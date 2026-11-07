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


# The Mica product each challenge page plays: (level 1, level 2).
APPS = {
    "llm01": ("Intranet", "Ops Assistant"),
    "llm02": ("HR Assistant", None),
    "llm03": ("Drive", "Drive"),
    "llm04": ("Model Hub", None),
    "llm05": ("Security Q&A", None),
    "llm06": ("Research Desk", None),
    "llm07": ("Customer Support", None),
    "llm08": ("Sales", "Sales Quotes"),
    "llm09": ("Knowledge Base", "My Notes"),
    "llm10": ("Company Store", "Store Admin"),
}


def app_name(challenge_id, level=1):
    """'Mica Intranet' etc., or None when the page has no app identity."""
    names = APPS.get(challenge_id)
    if not names:
        return None
    name = names[1] if level == 2 and names[1] else names[0]
    return f"{SHORT} {name}"
