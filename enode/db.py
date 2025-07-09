import mysql.connector
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASS"],
    "database": os.environ["DB_NAME"]
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def insert_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO users (id) VALUES (%s)", (user_id,))
        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert user {user_id}: {e}")
    finally:
        cursor.close()
        conn.close()


def insert_vehicle(vehicle, user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        vehicle_id = vehicle['id']
        vendor = vehicle.get('vendor')
        is_reachable = vehicle.get('isReachable')
        last_seen = vehicle.get('lastSeen')

        cursor.execute("""
            INSERT INTO vehicles (id, user_id, vendor, is_reachable, last_seen)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              vendor=VALUES(vendor), is_reachable=VALUES(is_reachable), last_seen=VALUES(last_seen)
        """, (
            vehicle_id, user_id, vendor, is_reachable, last_seen
        ))

        # Vehicle information
        info = vehicle.get("information", {})
        cursor.execute("""
            INSERT INTO vehicle_information (vehicle_id, vin, display_name, brand, model, year)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              vin=VALUES(vin), display_name=VALUES(display_name), brand=VALUES(brand),
              model=VALUES(model), year=VALUES(year)
        """, (
            vehicle_id, info.get('vin'), info.get('displayName'),
            info.get('brand'), info.get('model'), info.get('year')
        ))

        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert vehicle {vehicle.get('id')}: {e}")
    finally:
        cursor.close()
        conn.close()


def insert_charge_state(vehicle):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cs = vehicle.get('chargeState', {})
        vehicle_id = vehicle['id']
        now = datetime.utcnow()

        cursor.execute("""
            INSERT INTO charge_states (
                vehicle_id, recorded_at, charge_rate, time_remaining,
                is_fully_charged, is_plugged_in, is_charging, battery_level,
                range_km, battery_capacity, charge_limit, power_state, max_current
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            vehicle_id, now, cs.get('chargeRate'), cs.get('chargeTimeRemaining'),
            cs.get('isFullyCharged'), cs.get('isPluggedIn'), cs.get('isCharging'),
            cs.get('batteryLevel'), cs.get('range'), cs.get('batteryCapacity'),
            cs.get('chargeLimit'), cs.get('powerDeliveryState'), cs.get('maxCurrent')
        ))

        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert charge state: {e}")
    finally:
        cursor.close()
        conn.close()
