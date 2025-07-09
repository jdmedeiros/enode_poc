import requests
import time
import logging
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv

load_dotenv()  # only needed for local `.env` loading

ENODE_CLIENT_ID = os.environ["ENODE_CLIENT_ID"]
ENODE_CLIENT_SECRET = os.environ["ENODE_CLIENT_SECRET"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EnodeToken:
    """Stores Enode access token information with validation"""
    access_token: str
    token_type: str
    expires_in: int
    expires_at: float = field(init=False)
    scope: Optional[str] = None

    def __post_init__(self):
        self.expires_at = time.time() + self.expires_in

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60s buffer)"""
        return time.time() >= (self.expires_at - 60)


class EnodeAuthenticator:
    """Handles OAuth 2.0 authentication using standard requests library"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://enode-api.sandbox.enode.io",
        timeout: int = 30
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip('/')
        self.token_url = f"https://oauth.sandbox.enode.io/oauth2/token"
        self.timeout = timeout
        self.current_token: Optional[EnodeToken] = None
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def get_access_token(self) -> str:
        if not self.current_token or self.current_token.is_expired:
            self._refresh_token()
        return self.current_token.access_token

    def _refresh_token(self) -> None:
        """Fetch new access token using client credentials with Basic Auth"""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        auth = (self.client_id, self.client_secret)

        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = self.session.post(
                self.token_url,
                headers=headers,
                data=data,
                auth=auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            self._process_token_response(response.json())
            logger.info("Access token refreshed successfully")

        except requests.RequestException as e:
            logger.error(f"Token request failed: {e}")
            if e.response:
                logger.error(f"Response content: {e.response.text}")
            raise

    def _process_token_response(self, token_data: Dict[str, Any]) -> None:
        try:
            self.current_token = EnodeToken(
                access_token=token_data['access_token'],
                token_type=token_data['token_type'],
                expires_in=token_data['expires_in'],
                scope=token_data.get('scope')
            )
        except KeyError as e:
            logger.error(f"Missing required field in token response: {e}")
            logger.debug(f"Token response: {token_data}")
            raise ValueError(f"Invalid token response: missing {e}") from e

    def get_auth_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }


class BaseResource:
    def __init__(self, authenticator: EnodeAuthenticator):
        self.auth = authenticator

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'

        url = f"{self.auth.base_url}{endpoint}"
        headers = self.auth.get_auth_headers()

        try:
            response = self.auth.session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=self.auth.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            error_info = {
                "method": method,
                "url": url,
                "status_code": e.response.status_code if e.response else None,
                "error": str(e)
            }
            if e.response:
                try:
                    error_info["response"] = e.response.json()
                except json.JSONDecodeError:
                    error_info["response_text"] = e.response.text[:500]

            logger.error(f"API request failed: {json.dumps(error_info, indent=2)}")
            raise


class UserResource(BaseResource):
    def list_users(self, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        return self._request('GET', '/users', params=params).get('data', [])

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/users/{user_id}')


class VehicleResource(BaseResource):
    def list_vehicles(self, user_id: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        return self._request('GET', f'/users/{user_id}/vehicles', params=params).get('data', [])

    def get_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/vehicles/{vehicle_id}')

    def get_vehicle_location(self, vehicle_id: str) -> Dict[str, Any]:
        return self._request('GET', f'/vehicles/{vehicle_id}/location')

class CommandResource(BaseResource):
    def start_charging(self, user_id: str, vehicle_id: str) -> Dict[str, Any]:
        return self._request('POST', f'/users/{user_id}/vehicles/{vehicle_id}/commands/charging/start')

    def stop_charging(self, user_id: str, vehicle_id: str) -> Dict[str, Any]:
        return self._request('POST', f'/users/{user_id}/vehicles/{vehicle_id}/commands/charging/stop')

    def set_charge_limit(self, user_id: str, vehicle_id: str, limit: int) -> Dict[str, Any]:
        return self._request('POST',
            f'/users/{user_id}/vehicles/{vehicle_id}/commands/charging/set_limit',
            json_data={'limit': limit}
        )


class EnodeClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://enode-api.sandbox.enode.io",
        timeout: int = 30
    ):
        self.auth = EnodeAuthenticator(client_id, client_secret, base_url, timeout)
        self.users = UserResource(self.auth)
        self.vehicles = VehicleResource(self.auth)
        self.commands = CommandResource(self.auth)


# Example usage
if __name__ == "__main__":
    client = EnodeClient(
        client_id=ENODE_CLIENT_ID,
        client_secret=ENODE_CLIENT_SECRET,
        timeout=20
    )

    try:
        print("Fetching users...")
        users = client.users.list_users()
        print(f"Found {len(users)} users")

        for user in users:
            user_id = user['id']
            print(f"\nUser ID: {user_id}")

            print(f"Fetching vehicles for user {user_id}...")
            vehicles = client.vehicles.list_vehicles(user_id)
            print(f"User has {len(vehicles)} vehicles")

            for vehicle in vehicles:
                vehicle_id = vehicle['id']
                print(f"\nVehicle ID: {vehicle_id}")
                print("Basic vehicle info:")
                print(json.dumps(vehicle, indent=2))

                # Get full/enriched vehicle details
                try:
                    full_vehicle = client.vehicles.get_vehicle(vehicle_id)
                    print("Full vehicle details:")
                    print(json.dumps(full_vehicle, indent=2))
                except Exception as e:
                    print(f"Could not fetch full vehicle info for {vehicle_id}: {e}")

                # Get vehicle location if available
                location_stub = vehicle.get("location", {})
                lat = location_stub.get("latitude")
                lon = location_stub.get("longitude")

                if lat is not None and lon is not None:
                    try:
                        location = client.vehicles.get_vehicle_location(vehicle_id)
                        print("Vehicle location:")
                        print(json.dumps(location, indent=2))
                    except Exception as e:
                        print(f"Location API failed for vehicle {vehicle_id}: {e}")
                else:
                    print(f"Vehicle {vehicle_id} has no location data available.")

    except Exception as e:
        logger.exception("API operation failed")
        print(f"Error: {e}")
