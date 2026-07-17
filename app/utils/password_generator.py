"""
app/utils/password_generator.py
Generates temporary passwords for onboarding (PM item 7: "Generate Secure
Password"). 8 characters, mixed upper/lower/digits only — no symbols, per
decision: a password emailed to someone's inbox needs to be easy to
transcribe by hand or read off a phone screen without ambiguity about
which symbol was meant literally. Excludes visually ambiguous characters
(0/O, 1/I/l) for the same readability reason.
"""

import secrets
import string

_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I, O
_LOWER = "abcdefghijkmnpqrstuvwxyz"  # no l, o
_DIGITS = "23456789"  # no 0, 1
_ALPHABET = _UPPER + _LOWER + _DIGITS

PASSWORD_LENGTH = 8


def generate_temp_password() -> str:
    """
    Guarantees at least one uppercase, one lowercase, and one digit (so the
    result always satisfies _validate_password_complexity in
    app/schemas/auth.py by construction), fills the rest randomly, then
    shuffles so the guaranteed characters aren't predictably in the first
    three positions.
    """
    guaranteed = [
        secrets.choice(_UPPER),
        secrets.choice(_LOWER),
        secrets.choice(_DIGITS),
    ]
    remaining = [secrets.choice(_ALPHABET) for _ in range(PASSWORD_LENGTH - len(guaranteed))]
    chars = guaranteed + remaining
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
