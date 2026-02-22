import os
import atexit
import msal
import requests
import urllib3
import json
from typing import Optional, Dict, Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(ROOT_DIR, "token_cache.bin")


class AzureAuthManager:
    def __init__(self, config):
        self.client_id = config.azure_client_id
        self.tenant_id = config.azure_tenant_id


        self.app_scope = f"api://{self.client_id}/user_impersonation"

        self.scopes = ["User.Read", "email", self.app_scope]

        self.http_client = requests.Session()
        self.http_client.verify = False

        self.cache = msal.SerializableTokenCache()
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    self.cache.deserialize(f.read())
            except Exception:
                pass

        atexit.register(self._save_cache)

        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            token_cache=self.cache,
            http_client=self.http_client
        )

    def _save_cache(self):
        if self.cache.has_state_changed:
            with open(CACHE_FILE, "w") as f:
                f.write(self.cache.serialize())

    def login_interactive(self, persona_id: str, email: str):
        print(f"\n Authentication for : {email}")
        print(f"   Target : {self.app_scope}")

        flow = self.app.initiate_device_flow(scopes=self.scopes)

        if "user_code" not in flow:
            print(f" Error flow : {flow.get('error_description')}")
            return

        print(f"\n⚠  ACTION REQUIRED ⚠")
        print(f"1. Open : {flow['verification_uri']}")
        print(f"2. Enter the code : {flow['user_code']}")
        print(f"3. Connect to : {email}")

        result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            print(" Success ! Tokens retrieved.")
        else:
            print(f"⚠ Fail : {result.get('error_description')}")

    def get_cached_token_result(self, username_or_email: str) -> Optional[Dict[str, Any]]:

        username_target = username_or_email.lower().strip()

        accounts = self.app.get_accounts()
        target_account = None
        for acc in accounts:
            if username_target == acc.get("username", "").lower():
                target_account = acc
                break

        if target_account:

            try:
                result = self.app.acquire_token_silent(
                    scopes=[self.app_scope],
                    account=target_account
                )
                if result and "access_token" in result:
                    return result
            except Exception:
                pass

        try:
            cache_data = json.loads(self.cache.serialize())

            account_match = None
            for _, acct in cache_data.get("Account", {}).items():
                if acct.get("username", "").lower() == username_target:
                    account_match = acct
                    break

            if not account_match: return None

            haid = account_match.get("home_account_id")


            target_keyword = self.client_id

            best_token = None

            for key, tok in cache_data.get("AccessToken", {}).items():
                if tok.get("home_account_id") == haid:
                    scopes_in_token = tok.get("target", "").lower()

                    if self.client_id.lower() in scopes_in_token or "user_impersonation" in scopes_in_token:
                        return {"access_token": tok.get("secret"), "id_token": None}

        except Exception as e:
            print(f"[AUTH] Error cache reading : {e}")

        return None