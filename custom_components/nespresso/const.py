"""Constants for the Nespresso integration."""

DOMAIN = "nespresso"
CONF_MARKET = "market"
DEFAULT_MARKET = "it"
SCAN_INTERVAL_SECONDS = 60

COFFEE_FAMILY_MAP = {
    1: "Espresso",
    2: "Double Espresso",
    3: "Gran Lungo",
    4: "Mug",
    5: "Alto",
    6: "Carafe",
    7: "Alto XL",
}

MACHINE_STATUS_MAP = {
    0: "off",
    1: "on",
    2: "heating",
    3: "ready",
    4: "brewing",
    5: "cleaning",
    11: "standby",
    12: "ready",
}
