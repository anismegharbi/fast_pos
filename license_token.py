"""
Build the signed license token that the Voilà POS app expects.

The app's `requestLicense` function (decompiled from index.android.bundle)
expects the HTTP response to be:

    {
        "token": {
            "payload": { ... canonical fields ... },
            "signature": "<hex SHA-256>"
        }
    }

Where signature = SHA256( JSON.stringify(canonicalPayload) + "|" + SALT )

The canonical payload is built by the app's `canonicalPayload()` function
with keys sorted alphabetically and the `features` array sorted:

    {
        "deviceId":    string,
        "expiresAt":   number (epoch ms),
        "features":    string[],       # sorted
        "graceUntil":  number (epoch ms),
        "issuedAt":    number (epoch ms),
        "licenseKey":  string,
        "maxDevices":  number,
        "plan":        string,          # e.g. "pro", "demo"
        "status":      string           # "active", "expired", "blocked"
    }

The SALT is hardcoded in the bundle as:
    VOILA_POS_LICENSE_V1_SIGNING_SALT
"""

import hashlib
import json
import time
from datetime import datetime, timezone


SIGNING_SALT = "VOILA_POS_LICENSE_V1_SIGNING_SALT"

# Grace period: the app checks graceUntil to allow offline use.
# slot12 = 86400000ms = 1 day (offline allowed grace interval)
# slot13 = 60000ms = 1 minute  (offline NOT allowed interval)
# We set grace to 30 days to be generous.
GRACE_DAYS = 30


def _epoch_ms(dt: datetime) -> int:
    """Convert a datetime to epoch milliseconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _canonical_payload_json(payload: dict) -> str:
    """
    Reproduce the app's canonicalPayload() exactly.
    The app builds a NEW object with keys in this exact insertion order:
        deviceId, expiresAt, features, graceUntil, issuedAt,
        licenseKey, maxDevices, plan, status
    Then calls JSON.stringify on it.
    JavaScript's JSON.stringify preserves insertion order, so we must too.
    """
    canonical = {
        "deviceId":   payload["deviceId"],
        "expiresAt":  payload["expiresAt"],
        "features":   sorted(payload.get("features", [])),
        "graceUntil": payload["graceUntil"],
        "issuedAt":   payload["issuedAt"],
        "licenseKey": payload["licenseKey"],
        "maxDevices": payload["maxDevices"],
        "plan":       payload["plan"],
        "status":     payload["status"],
    }
    # Use separators without spaces to match JavaScript's default JSON.stringify
    return json.dumps(canonical, separators=(",", ":"))


def sign_payload(payload: dict) -> str:
    """
    Compute the SHA-256 signature the way the app's signPayload() does:
        SHA256( canonicalJSON + "|" + SALT )
    Returns the hex digest string.
    """
    canonical_json = _canonical_payload_json(payload)
    message = canonical_json + "|" + SIGNING_SALT
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def build_license_token(
    license_key: str,
    device_id: str,
    status: str,
    expires_at: datetime,
    plan: str = "pro",
    features: list[str] | None = None,
    max_devices: int = 1,
    offline_allowed: bool = True,
) -> dict:
    """
    Build the complete token object the app expects as the HTTP response body.
    Returns a dict ready to be serialized as JSON.
    """
    now_ms = int(time.time() * 1000)
    expires_ms = _epoch_ms(expires_at)
    grace_ms = expires_ms + (GRACE_DAYS * 86400000)

    payload = {
        "deviceId":       device_id,
        "expiresAt":      expires_ms,
        "features":       sorted(features or []),
        "graceUntil":     grace_ms,
        "issuedAt":       now_ms,
        "licenseKey":     license_key,
        "maxDevices":     max_devices,
        "offlineAllowed": offline_allowed,
        "plan":           plan,
        "status":         status,
    }

    signature = sign_payload(payload)

    return {
        "token": {
            "payload":   payload,
            "signature": signature,
        }
    }
