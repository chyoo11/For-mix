#coded by chyoo_eyes
import requests
import threading
import uuid
import time
import os
import random
import binascii
import secrets
from concurrent.futures import ThreadPoolExecutor
from ms4 import InfoTik
import SignerPy
RED = '\033[1;31m'
YELLOW = '\033[1;33m'
GREEN = '\033[2;32m'
CYAN = '\033[2;36m'
LIGHT_BLUE = '\033[1;34m'
seee = input(" [+] Session's File: ")
username = input(" [+] Username To Follow: ").strip()

with open(seee, "r") as f:
    sessions = list(set(i.strip() for i in f if i.strip()))

lock = threading.Lock()

try:
    user_info = InfoTik.TikTok_Info(username)
    user_id = user_info['id']
    sec_uid = user_info['secuid']
except Exception as e:
    print("[!] Failed to fetch user info:", str(e))
    exit()

def follow(session_id):
    try:
        model = "Redmi"
        brand = "Xiaomi"
        build = "RP1A.200720.011"

        params = {
            'user_id': str(user_id),
            'sec_user_id': sec_uid,
            'type': "1",
            'channel_id': "3",
            'from': "19",
            'from_pre': "13",
            'previous_page': "homepage_hot",
            'action_time': str(time.time()).replace(".", "")[:13],
            'is_network_available': "true",
            'device_platform': "android",
            'os': "android",
            'ssmix': "a",
            '_rticket': str(time.time()).replace(".", "")[:13],
            'cdid': str(uuid.uuid4()),
            'channel': "googleplay",
            'aid': "1233",
            'app_name': "musical_ly",
            'version_code': "390603",
            'version_name': "39.6.3",
            'manifest_version_code': "2023906030",
            'update_version_code': "2023906030",
            'ab_version': "39.6.3",
            'resolution': "1080*2220",
            'dpi': "440",
            'app_version': "39.6.3",
            'device_type': model,
            'device_brand': brand,
            'language': "en",
            'os_api': "30",
            'os_version': "11",
            'ac': "mobile",
            'is_pad': "0",
            'current_region': "US",
            'app_type': "normal",
            'sys_region': "US",
            'last_install_time': "1741496448",
            'mcc_mnc': "42103",
            'timezone_name': "Asia/Aden",
            'residence': "US",
            'app_language': "en",
            'carrier_region': "US",
            'timezone_offset': "10800",
            'host_abi': "arm64-v8a",
            'locale': "en",
            'ac2': "lte",
            'uoo': "0",
            'op_region': "US",
            'build_number': "39.6.3",
            'region': "US",
            'ts': str(round(random.uniform(1.2, 1.6) * 100000000) * -1),
            'iid': str(random.randint(1, 10**19)),
            'device_id': str(random.randint(1, 10**19)),
            'openudid': str(binascii.hexlify(os.urandom(8)).decode()),
        }

        secret = secrets.token_hex(16)
        cookies = {
            "sessionid": session_id,
            "passport_csrf_token": secret,
            "passport_csrf_token_default": secret,
            "tt-target-idc":'useast1a',
            "sid_tt": session_id,
            "sid_tt": session_id,
            "store-country-code-src": 'uid',
            "store-country-code": 'iq',
            "store-idc":'alisg'
        }

        headers = {
            'User-Agent': f"com.zhiliaoapp.musically/2023906030 (Linux; U; Android 11; en; {model}; Build/{build}; Cronet/TTNetVersion:a482972f)",
            'x-tt-passport-csrf-token': secret,
            'Cookie': f"sessionid={session_id}"
        }

        signature = SignerPy.sign(params=params, cookie=cookies)

        headers.update({
            'x-ss-req-ticket': signature['x-ss-req-ticket'],
            'x-ss-stub': signature['x-ss-stub'],
            'x-argus': signature["x-argus"],
            'x-gorgon': signature["x-gorgon"],
            'x-khronos': signature["x-khronos"],
            'x-ladon': signature["x-ladon"],
        })

        url = "https://api16-core-c-alisg.tiktokv.com/aweme/v2/follow/feed/"
        response = requests.get(url, params=params, headers=headers)

        with lock:
            if '"status_code":0' in response.text:
                print("success✅")
            else:
                print(response.text)

    except Exception as ex:
        with lock:
            print(f"[!] ERROR   | {session_id} -> {str(ex)}")

with ThreadPoolExecutor(max_workers=50) as executor:
    executor.map(follow, sessions)
