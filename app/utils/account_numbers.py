from __future__ import annotations

import secrets

from app.core.config import settings


def generate_account_number() -> str:
    return f"40{secrets.randbelow(10**10):010d}"


def generate_iban(account_number: str) -> str:
    checksum = 98 - ((int(f"{account_number}182700") % 97) or 1)
    return f"{settings.iban_country_code}{checksum:02d}BANK{account_number}"


def generate_masked_pan() -> tuple[str, str]:
    raw = f"476173{secrets.randbelow(10**10):010d}"
    last4 = raw[-4:]
    masked = f"{raw[:4]} **** **** {last4}"
    return masked, last4

