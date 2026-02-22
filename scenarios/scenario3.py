import datetime
import time

def get_timestamp_id():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def execute(ctx):

    for persona in ctx.config.personas:
        run_checks(ctx, persona)

def run_checks(ctx, persona_conf):
    ctx.set_context("SCENARIO_3", persona_conf)

    role = persona_conf.persona_id
    email = persona_conf.username
    password = persona_conf.password


    if role != "GUEST":
        try:
            ctx.client._establish_azure_session()
        except Exception:
            pass

    auth_methods = getattr(ctx, 'current_auth_methods', [])
    has_azure_mfa = "mfa" in auth_methods

    # ---------------------------------------------------------
    # INITIAL AUTHENTICATION (To get current persona's token)
    # ---------------------------------------------------------
    if role != "GUEST":
        try:
            r = ctx.client.post("/rest/user/login", json={"email": email, "password": password})
            if r.status_code == 200:
                token = r.json().get('authentication', {}).get('token')
                ctx.auth_context.bearer_token = token
        except Exception:
            pass

    # ---------------------------------------------------------
    # C1: Password Strength (Weak Account Creation)
    # ---------------------------------------------------------
    try:
        email_test = f"weak_{get_timestamp_id()}_{role}@test.com"
        payload = {
            "email": email_test,
            "password": "12345",
            "passwordRepeat": "12345",
            "securityQuestion": {"id": 1, "answer": "test"}
        }
        r = ctx.client.post("/api/Users", json=payload)

        if r.status_code == 201:
            verdict = "VULNERABLE"
            details = "Account creation with weak password accepted"
        else:
            verdict = "SECURE"
            details = "Strict password policy enforced"

        ctx.log_verdict("Weak Password Policy", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Weak Password Policy", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # C2: Login Admin (SQL Injection)
    # ---------------------------------------------------------
    try:
        payload = {"email": "' OR 1=1--", "password": "x"}
        r = ctx.client.post("/rest/user/login", json=payload)

        if r.status_code == 200 and "token" in r.json().get("authentication", {}):
            verdict = "VULNERABLE"
            details = "SQLi Login Bypass successful"
        else:
            verdict = "SECURE"
            details = "SQL Injection blocked"

        ctx.log_verdict("SQL Injection (Admin Account Takeover)", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("SQL Injection (Admin Account Takeover)", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # C3: 2FA Bypass (Testing Enforcement)
    # ---------------------------------------------------------
    try:
        if has_azure_mfa:
            verdict = "SECURE"
            details = "Protected by Azure MFA (Claim 'amr: mfa' verified)"
            status_code = "MFA_OK"
        else:
            payload = {"email": "admin@juice-sh.op", "password": "admin123"}
            r = ctx.client.post("/rest/user/login", json=payload)
            status_code = r.status_code

            if r.status_code == 200:
                verdict = "VULNERABLE"
                details = "Direct Admin access without MFA"
            else:
                verdict = "SECURE"
                details = "MFA Required"

        ctx.log_verdict("MFA Enforcement Check", status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("MFA Enforcement Check", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # C4: Login Untrusted Location
    # ---------------------------------------------------------
    try:
        payload = {"email": "admin@juice-sh.op", "password": "admin123"}
        headers = {"X-Forwarded-For": "1.2.3.4", "User-Agent": "EvilBot/1.0"}

        r = ctx.client.post("/rest/user/login", json=payload, headers=headers)
        status_code = r.status_code

        if r.status_code == 200:
            verdict = "VULNERABLE"
            details = "Login accepted from suspicious IP (No Geo-IP blocking)"
        else:
            verdict = "SECURE"
            details = "Geo-IP blocking active or request intercepted"

        ctx.log_verdict("Context-Based Access Control (Geo)", status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Context-Based Access Control (Geo)", "ERR", str(e), "ERR")


    # ---------------------------------------------------------
    # C5: Admin Session Bootstrap
    # ---------------------------------------------------------
    try:
        r = ctx.client.get("/rest/admin/application-configuration")

        if role == "ADMIN":
            verdict = "NORMAL"
            details = "Legitimate access"
        else:
            if r.status_code == 200:
                verdict = "VULNERABLE"
                details = "Standard User accessed Admin functions"
            else:
                verdict = "SECURE"
                details = "Admin session bootstrap refused"

        ctx.log_verdict("Vertical Privilege Escalation", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Vertical Privilege Escalation", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # C6: Login MC SafeSearch
    # ---------------------------------------------------------
    try:
        target_email = "mc.safesearch@juice-sh.op"
        target_pass = "Mr. N00dles"

        r = ctx.client.post("/rest/user/login", json={"email": target_email, "password": target_pass})

        if r.status_code == 200:
            if email == target_email:
                verdict = "NORMAL"
                details = "Legitimate login (Self)"
            else:
                verdict = "VULNERABLE"
                details = "USER account compromised (OSINT)"
        else:
            verdict = "SECURE"
            details = "Account protected"

        ctx.log_verdict("Credential Stuffing / Weak Account", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Credential Stuffing / Weak Account", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # C7: Reset Jim Password
    # ---------------------------------------------------------
    try:
        target_jim = "jim@juice-sh.op"
        r = ctx.client.get(f"/rest/user/security-question?email={target_jim}")

        if r.status_code == 200:
            data = r.json()
            if "question" in data:
                question_text = str(data.get('question'))
                if email == target_jim:
                    verdict = "NORMAL"
                    details = "USER sees their own question"
                else:
                    verdict = "VULNERABLE"
                    details = f"Info leak: {question_text[:30]}..."
            else:
                verdict = "SECURE"
                details = "No security question field"
        else:
            verdict = "SECURE"
            details = "Security question masked"

        ctx.log_verdict("Info Disclosure (Security Question)", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Info Disclosure (Security Question)", "ERR", str(e), "ERR")