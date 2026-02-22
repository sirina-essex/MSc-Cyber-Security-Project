import concurrent.futures
import time
import hmac
import hashlib
import base64

# SECRET shared (Simulation of key)
FIDO_SECRET = b"JUICE_SHOP_SECURE_KEY_2024"


def generate_fido_signature(path):
    signature = hmac.new(FIDO_SECRET, path.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')


def execute(ctx):
    for persona in ctx.config.personas:
        run_checks_for_persona(ctx, persona)


def run_checks_for_persona(ctx, persona_conf):
    ctx.set_context("SCENARIO_1", persona_conf)

    role = persona_conf.persona_id
    email = persona_conf.username
    password = persona_conf.password

    # --- Authentication ---
    if role != "GUEST":
        try:
            r = ctx.client.post("/rest/user/login", json={"email": email, "password": password})
            if r.status_code == 200:
                token = r.json().get('authentication', {}).get('token')
                ctx.auth_context.bearer_token = token
            else:
                ctx.log_verdict("Login", r.status_code, "Auth Failed", "ERROR")
        except Exception as e:
            ctx.log_verdict("Login", "ERR", f"Exception: {e}", "ERROR")

    # ---------------------------------------------------------
    # A1: Exposed Metrics & FIDO2 Enforced
    # ---------------------------------------------------------

    FIDO_SWITCH = True
    # True = Activate FIDO


    try:
        if FIDO_SWITCH:

            if role == "ADMIN":
                ctx.log_verdict("High Assurance Auth (FIDO2)", 200, "Privileged access granted with high-assurance authentication", "ACCESS_POLICY")

                headers = {"X-Fido-Switch": "ON"}

                # target_path = "/metrics"
                # sig = generate_fido_signature(target_path)

                r = ctx.client.get("/metrics", headers=headers)

                if r.status_code == 401:
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", 401, "High-assurance authentication required for privileged action", "SENSITIVE_OPERATION")
                else:
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", r.status_code, "Unexpected (Should be blocked)", "UNKNOWN")
            else:
                r = ctx.client.get("/metrics")
                if r.status_code != 200:
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", r.status_code, "Access refused", "SECURE")
                else:
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", 200, "Sensitive data exposed", "VULNERABLE")

        else:
            ctx.log_verdict("High Assurance Auth (FIDO2)", 200, "High identity assurance not required for operation", "INFO")

            r = ctx.client.get("/metrics")

            if r.status_code == 200:
                if role == "ADMIN":
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", 200, "Admin access allowed", "NORMAL")
                else:
                    ctx.log_verdict("Sensitive Data Exposure (Metrics)", 200, "Sensitive data exposed", "VULNERABLE")
            else:
                ctx.log_verdict("Sensitive Data Exposure (Metrics)", r.status_code, "Access refused", "SECURE")

    except Exception as e:
        ctx.log_verdict("Sensitive Data Exposure (Metrics)", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # A2: Privileged Access (Governance)
    # ---------------------------------------------------------
    try:
        r = ctx.client.get("/rest/admin/application-configuration")

        if role == "ADMIN":
            if r.status_code == 200:
                ctx.log_verdict("Broken Access Control (Vertical)", 200, "Admin recognized and allowed", "NORMAL")
            else:
                ctx.log_verdict("Broken Access Control (Vertical)", r.status_code, f"Admin blocked", "UNKNOWN")
        else:
            if r.status_code == 200:
                ctx.log_verdict("Broken Access Control (Vertical)", 200, "Privilege Escalation", "VULNERABLE")
            else:
                ctx.log_verdict("Broken Access Control (Vertical)", r.status_code, "Properly blocked", "SECURE")
    except Exception as e:
        ctx.log_verdict("Broken Access Control (Vertical)", "ERR", str(e), "ERR")

    # ---------------------------------------------------------
    # A3: Multiple Actions
    # ---------------------------------------------------------
    try:
        payload = {"message": f"Spam {role} {time.time()}", "author": email}

        def send_request():
            try:
                return ctx.client.put("/rest/products/1/reviews", json=payload).status_code
            except:
                return 0

        results_codes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_request) for _ in range(5)]
            for future in concurrent.futures.as_completed(futures):
                results_codes.append(future.result())

        success_count = results_codes.count(201) + results_codes.count(200)
        final_code = str(results_codes[0]) if results_codes else "ERR"

        if role == "ADMIN":
            if success_count >= 1:
                ctx.log_verdict("Rate Limiting & Race Condition", "200/201", f"Admin allowed ({success_count}/5)", "NORMAL")
            else:
                ctx.log_verdict("Rate Limiting & Race Condition", str(results_codes), "Admin blocked", "UNKNOWN")
        elif role == "GUEST":
            if success_count > 0:
                ctx.log_verdict("Rate Limiting & Race Condition", "201", "Guest injected data", "VULNERABLE")
            else:
                ctx.log_verdict("Rate Limiting & Race Condition", "401", "Guest blocked", "SECURE")
        else:
            if success_count > 1:
                ctx.log_verdict("Rate Limiting & Race Condition", "201 (Mult)", "Race condition successfull", "VULNERABLE")
            else:
                ctx.log_verdict("Rate Limiting & Race Condition", "201", "Logic respected", "SECURE")

    except Exception as e:
        ctx.log_verdict("Rate Limiting & Race Condition", "ERR", str(e), "ERR")