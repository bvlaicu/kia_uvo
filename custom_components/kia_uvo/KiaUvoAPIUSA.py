import base64
import logging
import sys

from datetime import timedelta, datetime
import json
import random
import string
import secrets

import pytz
import requests
from urllib.parse import parse_qs, urlparse
import uuid
import time

from .const import DOMAIN, BRANDS, BRAND_HYUNDAI, BRAND_KIA, DATE_FORMAT, VEHICLE_LOCK_ACTION
from .KiaUvoApiImpl import KiaUvoApiImpl
from .Token import Token, UsaToken

_LOGGER = logging.getLogger(__name__)


class KiaUvoAPIUSA(KiaUvoApiImpl):

    def api_headers(self) -> dict:
        # offset from UTC. TODO actually read this from the system
        offset = -7
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "apptype": "L",
            "appversion": "4.10.0",
            "clientid": "MWAMOBILE",
            "from": "SPA",
            "host": self.BASE_URL,
            "language": "0",
            "offset": str(offset),
            "ostype": "Android",
            "osversion": "11",
            "secretkey": "98er-w34rf-ibf3-3f6h",
            "to": "APIGW",
            "tokentype": "G",
            "user-agent": "okhttp/3.12.1",
        }
        # should produce something like "Mon, 18 Oct 2021 07:06:26 GMT". May require adjusting locale to en_US
        date = datetime.now(tz=pytz.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers['date'] = date
        headers['deviceid'] = self.device_id
        return headers

    def __init__(
        self,
        username: str,
        password: str,
        region: int,
        brand: int,
        use_email_with_geocode_api: bool = False,
        pin: str = "",
    ):
        super().__init__(username, password, region, brand, use_email_with_geocode_api, pin)

        # Randomly generate a plausible device id on startup
        self.device_id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(22)) + ':' + secrets.token_urlsafe(105)

        self.BASE_URL: str = "api.owners.kia.com"
        self.API_URL: str = "https://" + self.BASE_URL + "/apigw/v1/"


        self.old_vehicle_status = {}

    def login(self) -> Token:
        username = self.username
        password = self.password

        ### Sign In with Email and Password and Get Authorization Code ###

        url = self.API_URL + "prof/authUser"

        data = {
            "deviceKey": "",
            "deviceType": 2,
            "userCredential": {
            "userId": username, "password": password
            }
        }
        headers = self.api_headers()
        response = requests.post(url, json=data, headers=headers)
        _LOGGER.debug(f"{DOMAIN} - Sign In Response {response.text}")
        session_id = response.headers.get('sid')
        if not session_id:
            raise Exception(f"no session id returned in login. Response: {response.text} headers {response.headers} cookies {response.cookies}")
        _LOGGER.debug(f"got session id {session_id}")

        ### Get Vehicles ###
        url = self.API_URL + "ownr/gvl"
        headers = self.api_headers()
        headers["sid"] = session_id
        response = requests.get(url, headers=headers)
        _LOGGER.debug(f"{DOMAIN} - Get Vehicles Response {response.text}")
        response = response.json()
        vehicle_summary = response["payload"]["vehicleSummary"]
        vehicle_name = vehicle_summary[0]["nickName"]
        vehicle_id = vehicle_summary[0]["vehicleIdentifier"]
        vehicle_vin = vehicle_summary[0]["vin"]
        vehicle_key = vehicle_summary[0]['vehicleKey']

        token = UsaToken(session_id, vehicle_vin, vehicle_id, vehicle_name, vehicle_key)

        return token

    def get_cached_vehicle_status(self, token: Token):
        url = self.API_URL + "cmm/gvi"
        headers = self.api_headers()
        headers['sid'] = token.sid
        headers['vinkey'] = token.vehicle_key

        body = {
                "vehicleConfigReq": {
                    "airTempRange": "0",
                    "maintenance": "0",
                    "seatHeatCoolOption": "0",
                    "vehicle": "1",
                    "vehicleFeature": "0"
                },
                "vehicleInfoReq": {
                    "drivingActivty": "0",
                    "dtc": "1",
                    "enrollment": "1",
                    "functionalCards": "0",
                    "location": "1",
                    "vehicleStatus": "1",
                    "weather": "0"
                },
                "vinKey": [
                    token.vehicle_key
                ]
            }
        _LOGGER.debug(f"sending get vehicle info request ${body} with session id ${token.sid}")
        response = requests.post(url, json=body, headers=headers)
        _LOGGER.debug(f"got response {response.text}")
        response_body = response.json()
        return response_body
    def get_location(self, token: Token):
        pass
    def get_pin_token(self, token: Token):
        pass
    def update_vehicle_status(self, token: Token):
        pass

    def lock_action(self, token: Token, action):
        pass

    def start_climate(self, token: Token, set_temp, duration, defrost, climate, heating):
        pass

    def stop_climate(self, token: Token):
        pass
    def check_action_status(self, token: Token, pAuth, transactionId):
        pass
    def start_charge(self, token: Token):
        pass

    def stop_charge(self, token: Token):
        pass