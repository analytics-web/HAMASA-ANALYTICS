import random, time
from typing import Dict



# change to redis on production
otp_store:  Dict[str, dict] = {}


def generate_otp(phone: str, expiry: int = 300) -> str:
    """
    Generate a 6-digit OTP, store with expiry (default 5 minutes).
    """
    otp = str(random.randint(100000, 999999))
    otp_store[phone] = {
        "otp": otp,
        "expires_at": time.time() + expiry
    }
    return otp

def verify_otp(phone: str, otp: str) -> bool:
    """
    Verify OTP for phone. Returns True if valid, False otherwise.
    """
    record = otp_store.get(phone)

    if not record:
        return False

    # Check expiry
    if time.time() > record["expires_at"]:
        del otp_store[phone]  # cleanup
        return False

    # Match OTP
    if record["otp"] == otp:
        del otp_store[phone]  # one-time use
        return True

    return False