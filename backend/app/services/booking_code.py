"""Generate human-friendly booking codes.

8 characters, base32 alphabet excluding visually ambiguous chars (0/O, 1/I/L).
~32^8 = 1.1 trillion combinations — collisions are vanishingly rare, but the
INSERT path retries on uniqueness violation to handle the case.
"""
import secrets

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LENGTH = 8


def generate_booking_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
