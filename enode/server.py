from flask import Flask, request, jsonify
import hmac
import hashlib
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Your Enode webhook secret
# python3 -c "import secrets; print(secrets.token_urlsafe(32))" past the result below and create the webhook with it
WEBHOOK_SECRET = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

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
