import time
import requests
import urllib3
import json
import base64
from datetime import datetime, timezone
from typing import Optional, Any

from run.models import AuditResult, RunnerConfig, PersonaConfig, AuthContext
from run.attempt_record import AttemptRecord, map_http_to_functional_outcome, SCHEMA_VERSION_ATTEMPT_RECORD
from run.constants import TARGET_SYSTEM, TECH_STATUS_OK, ACTION_TYPE_HTTP_CALL
from run.id_utils import format_attempt_id
from run.auth_manager import AzureAuthManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from run.action_executor import hash_response_body_bytes
except ImportError:
    def hash_response_body_bytes(content):
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SmartClient:
    def __init__(self, context):
        self.ctx = context
        self.session = requests.Session()
        self.session.verify = False
        self.azure_manager = AzureAuthManager(self.ctx.config)

    def _establish_azure_session(self):

        if self.ctx.azure_authenticated:
            return

        persona = self.ctx.current_persona_conf
        azure_email = getattr(persona, 'azure_email', None)

        if not azure_email:
            self.ctx.azure_authenticated = True
            return

        result = self.azure_manager.get_cached_token_result(azure_email)
        access_token = result.get("access_token") if result else None

        if access_token:
            real_user = "Unknown Identity"
            auth_methods = []

            try:
                parts = access_token.split('.')
                if len(parts) > 1:
                    payload = parts[1]

                    # FIX: correct base64 padding (works for any payload length)
                    padded = payload + '=' * (-len(payload) % 4)

                    decoded = base64.urlsafe_b64decode(padded)
                    claims = json.loads(decoded)

                    upn = claims.get('upn')
                    preferred = claims.get('preferred_username')
                    email_claim = claims.get('email')
                    unique_name = claims.get('unique_name')
                    oid = claims.get('oid')

                    real_user = upn or preferred or email_claim or unique_name or "Inconnu"

                    auth_methods = claims.get('amr', [])

                    self.ctx.current_token_claims = claims
                    self.ctx.current_auth_methods = auth_methods

                    # DEBUG (needed to fix APIM RBAC check): display stable identifiers
                    print("\n[JWT DEBUG CLAIMS]")
                    print(f"UPN: {upn}")
                    print(f"PREFERRED_USERNAME: {preferred}")
                    print(f"EMAIL: {email_claim}")
                    print(f"UNIQUE_NAME: {unique_name}")
                    print(f"OID: {oid}\n")

            except Exception as e:
                print(f"[Authentication] ⚠ Unable to decode Claims : {e}")

            mfa_status = " MFA DETECTED !" if "mfa" in auth_methods else "⚠ No MFA"
            print(f"[Authentication] Token for {persona.persona_id} ({real_user}) | {mfa_status}")

            self.session.headers.update({
                "Authorization": f"Bearer {access_token}"
            })

            if self.ctx.auth_context:
                self.ctx.auth_context.bearer_token = access_token

            print(f"[Authentication] Authentication configured (Mode API/Bearer).")
            self.ctx.azure_authenticated = True

        else:
            print(f"[Authentication] ⚠ No valid token found for {azure_email}.")
            self.ctx.azure_authenticated = True

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        self._establish_azure_session()

        base = self.ctx.config.target.base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        full_url = f"{base}{path}"

        headers = kwargs.get("headers", {})
        if headers is None:
            headers = {}

        if "Authorization" not in headers and "Authorization" not in self.session.headers:
            if self.ctx.auth_context and self.ctx.auth_context.bearer_token:
                headers["Authorization"] = f"Bearer {self.ctx.auth_context.bearer_token}"

        kwargs["headers"] = headers

        self.ctx.attempt_seq += 1
        attempt_id = format_attempt_id(self.ctx.run_id, self.ctx.attempt_seq)
        ts_start = utc_now_iso()
        start_perf = time.perf_counter()

        resp = None
        status_code = 0
        technical_status = "UNKNOWN"
        error_type = None

        try:
            resp = self.session.request(method, full_url, verify=False, **kwargs)
            technical_status = TECH_STATUS_OK
            status_code = resp.status_code
        except Exception as e:
            technical_status = "CLIENT_ERROR"
            error_type = str(type(e).__name__)

            class MockResp:
                content = b""
                status_code = 0

            resp = MockResp()

        duration_ms = int((time.perf_counter() - start_perf) * 1000)

        rec = AttemptRecord(
            schema_version=SCHEMA_VERSION_ATTEMPT_RECORD,
            run_id=self.ctx.run_id,
            attempt_seq=self.ctx.attempt_seq,
            attempt_id=attempt_id,
            scenario_id=self.ctx.current_scenario_id,
            persona_id=self.ctx.current_persona_id,
            action_id=f"step_{self.ctx.attempt_seq}",
            action_name=f"{method} {path}",
            action_type=ACTION_TYPE_HTTP_CALL,
            target_system=TARGET_SYSTEM,
            endpoint=path,
            http_method=method,
            ts_start_utc=ts_start,
            ts_end_utc=utc_now_iso(),
            duration_ms=duration_ms,
            technical_status=technical_status,
            functional_outcome=map_http_to_functional_outcome(status_code, technical_status),
            http_status_code=status_code,
            error_type=error_type,
            error_message_hash=None,
            response_size_bytes=len(resp.content) if hasattr(resp, 'content') else 0,
            response_body_hash=hash_response_body_bytes(resp.content) if hasattr(resp, 'content') else None,
            request_fingerprint=None
        )

        if self.ctx.json_writer:
            self.ctx.json_writer.write(rec)
        if self.ctx.csv_writer:
            self.ctx.csv_writer.write(rec)

        return resp

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


class ScenarioContext:
    def __init__(self, config: RunnerConfig, run_id: str, json_writer, csv_writer, report_writer):
        self.config = config
        self.run_id = run_id
        self.json_writer = json_writer
        self.csv_writer = csv_writer
        self.report_writer = report_writer
        self.attempt_seq = 0
        self.current_scenario_id = "UNKNOWN"
        self.current_persona_id = "UNKNOWN"
        self.current_persona_conf = None
        self.auth_context: Optional[AuthContext] = None
        self.azure_authenticated = False
        self.client = SmartClient(self)

        self.current_token_claims = {}
        self.current_auth_methods = []

    def set_context(self, scenario_id: str, persona: PersonaConfig):
        self.current_scenario_id = scenario_id
        self.current_persona_id = persona.persona_id
        self.current_persona_conf = persona
        self.auth_context = AuthContext(persona.persona_id, None)
        self.azure_authenticated = False
        self.client.session = requests.Session()
        self.client.session.verify = False
        self.current_token_claims = {}
        self.current_auth_methods = []

    def log_verdict(self, name: str, status_code: Any, details: str, verdict: str):
        res = AuditResult(
            scenario_id=self.current_scenario_id,
            name=name,
            persona_id=self.current_persona_id,
            http_code=str(status_code),
            verdict=verdict,
            details=details,
            timestamp=utc_now_iso()
        )
        if self.report_writer:
            self.report_writer.add_result(res)
        print(f"[{self.current_scenario_id}] {name} | {self.current_persona_id} | {str(status_code)} | {verdict} | {details}")