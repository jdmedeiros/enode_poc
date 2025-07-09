import os
from dotenv import load_dotenv
from db import insert_user, insert_vehicle, insert_charge_state
from flask import Flask, request, jsonify
import hmac
import hashlib
import logging
import json

# Load .env if running locally (has no effect in systemd)
load_dotenv()

# Your Enode webhook secret
WEBHOOK_SECRET = os.environ["ENODE_WEBHOOK_SECRET"]

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC-SHA1 signature from Enode."""
    if signature.startswith("sha1="):
        signature = signature[5:]
    computed_hmac = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(computed_hmac, signature)

@app.route("/webhook", methods=["POST"])
def enode_webhook():
    # Get raw payload and headers
    raw_payload = request.get_data()
    signature = request.headers.get("x-enode-signature", "")
    delivery_id = request.headers.get("x-enode-delivery", "unknown")

    # Compute HMAC-SHA1
    if signature.startswith("sha1="):
        stripped_signature = signature[5:]
    else:
        stripped_signature = signature

    computed_hmac = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=raw_payload,
        digestmod=hashlib.sha1
    ).hexdigest()

    # Log request info
    logging.info(f"Delivery ID: {delivery_id}")
    logging.info(f"Raw payload: {raw_payload}")
    logging.info(f"Enode signature: {signature}")
    logging.info(f"Computed HMAC: {computed_hmac}")

    # Signature check
    if not hmac.compare_digest(computed_hmac, stripped_signature):
        logging.warning(f"Invalid signature for delivery {delivery_id}")
        return jsonify({"error": "Invalid signature"}), 400

    # Parse JSON payload
    try:
        events = json.loads(raw_payload)
        logging.info(f"✅ Valid webhook. {len(events)} event(s) received:")
        for event in events:
            logging.info(json.dumps(event, indent=2))
            if event['event'] in ("enode:webhook:test", "system:heartbeat"):
                break
            user_id = event['user']['id']
            vehicle = event['vehicle']

            # Insert user
            insert_user(user_id)

            # Insert or update vehicle and vehicle information
            insert_vehicle(vehicle, user_id)

            # Insert charge state snapshot (time-series)
            insert_charge_state(vehicle)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.exception("Failed to parse webhook payload")
        return jsonify({"error": "Invalid JSON"}), 500

logging.basicConfig(
    filename='/var/log/enode_webhook.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080)
