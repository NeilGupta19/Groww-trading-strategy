"""
Authentication wrapper for the Groww API (TOTP flow — no daily re-approval).
"""

import sys
import os
import pyotp
from growwapi import GrowwAPI

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import credentials


def get_client():
    totp = pyotp.TOTP(credentials.TOTP_SECRET).now()
    access_token = GrowwAPI.get_access_token(api_key=credentials.API_KEY, totp=totp)
    return GrowwAPI(access_token)
