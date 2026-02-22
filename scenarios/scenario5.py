import datetime


def get_timestamp_id():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def solve_captcha(ctx):
    try:
        r = ctx.client.get("/rest/captcha")
        if r.status_code == 200:
            data = r.json()
            answer = str(eval(str(data.get("captcha"))))
            return data.get("captchaId"), answer
    except:
        pass
    return None, None


def execute(ctx):
    admin_token = None

    admin_persona = next((p for p in ctx.config.personas if "ADMIN" in p.persona_id.upper()), None)

    if admin_persona:
        try:
            r = ctx.client.post("/rest/user/login",
                                json={"email": admin_persona.username, "password": admin_persona.password})
            if r.status_code == 200:
                admin_token = r.json().get('authentication', {}).get('token')
        except:
            print("[WARN] Unable to retrieve Admin token for XSS verification")

    for persona in ctx.config.personas:
        run_checks(ctx, persona, admin_token)


def run_checks(ctx, persona_conf, global_admin_token):
    ctx.set_context("SCENARIO_5", persona_conf)

    role = persona_conf.persona_id

    # Auth
    if role != "GUEST":
        try:
            r = ctx.client.post("/rest/user/login",
                                json={"email": persona_conf.username, "password": persona_conf.password})
            if r.status_code == 200:
                ctx.auth_context.bearer_token = r.json().get('authentication', {}).get('token')
        except:
            pass

    # ---------------------------------------------------------
    # E1: Persistent XSS
    # ---------------------------------------------------------
    try:
        unique_marker = f"XSS_{get_timestamp_id()}_{role}"
        # Raw Payload: <script>...</script>
        xss_raw = f"<script>alert('{unique_marker}')</script>"

        captcha_id, captcha_answer = solve_captcha(ctx)

        if captcha_id and captcha_answer:
            payload = {
                "comment": xss_raw,
                "rating": 4,
                "captchaId": captcha_id,
                "captcha": captcha_answer
            }

            # 1. THE INJECTION (POST)
            r = ctx.client.post("/api/Feedbacks", json=payload)
            injection_code = r.status_code

            # 2. THE AUDIT (DB VERIFICATION via Admin Token)
            if injection_code == 201:
                if global_admin_token:

                    old_token = ctx.auth_context.bearer_token
                    ctx.auth_context.bearer_token = global_admin_token

                    check = ctx.client.get("/api/Feedbacks")

                    ctx.auth_context.bearer_token = old_token

                    if check.status_code == 200:
                        feedbacks = check.json().get("data", [])
                        found = False
                        is_vulnerable = False

                        for fb in feedbacks:
                            if unique_marker in str(fb.get("comment")):
                                found = True
                                stored_comment = fb.get("comment")
                                if "<script>" in stored_comment:
                                    is_vulnerable = True
                                break

                        if found and is_vulnerable:
                            verdict = "VULNERABLE"
                            details = "Malicious script stored RAW in database"
                        elif found and not is_vulnerable:
                            verdict = "SECURE"
                            details = "Injection stored but sanitized"
                        else:
                            verdict = "VULNERABLE (POTENTIAL)"
                            details = "Injection accepted (201) but trace not found via API"
                    else:
                        verdict = "UNKNOWN"
                        details = "Failed to read Admin data for verification"
                else:
                    verdict = "VULNERABLE (SUSPECTED)"
                    details = "Injection accepted (201) - No Admin token to verify"
            else:
                verdict = "SECURE"
                details = f"Injection blocked by WAF/Input Validation (Code {injection_code})"

        else:
            verdict = "UNKNOWN"
            details = "Captcha Solver Failed"
            injection_code = "0"

        ctx.log_verdict("Stored Cross-Site Scripting (XSS)", injection_code, details, verdict)

    except Exception as e:
        ctx.log_verdict("Stored Cross-Site Scripting (XSS)", "ERR", str(e), "ERROR")