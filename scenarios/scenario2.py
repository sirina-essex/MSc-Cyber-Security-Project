import time



def _establish_azure_session_if_available(ctx):
    try:
        if hasattr(ctx.client, "_establish_azure_session"):
            ctx.client._establish_azure_session()
    except Exception:
        pass


def _bearer_from_ctx(ctx):
    try:
        return getattr(ctx.auth_context, "bearer_token", None)
    except Exception:
        return None


def _auth_headers(ctx):
    token = _bearer_from_ctx(ctx)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get_csrf_token(ctx):

    try:
        r = ctx.client.get("/rest/csrf")
        if r.status_code == 200:
            data = r.json()
            return data.get("csrfToken")
    except Exception:
        pass
    return None


def solve_captcha(ctx):
    try:
        r = ctx.client.get("/rest/captcha")
        if r.status_code == 200:
            data = r.json()
            return data.get("captchaId"), str(eval(str(data.get("captcha"))))
    except Exception:
        pass
    return None, None


# -----------------------------
# Scenario entry points
# -----------------------------
def execute(ctx):
    for persona in ctx.config.personas:
        run_checks(ctx, persona)


def run_checks(ctx, persona_conf):
    ctx.set_context("SCENARIO_2", persona_conf)

    role = persona_conf.persona_id
    email = persona_conf.username
    password = persona_conf.password

    # ---------------------------------------------------------
    # 1) Authentification
    # ---------------------------------------------------------
    if role != "GUEST":
        _establish_azure_session_if_available(ctx)
        try:
            r = ctx.client.post("/rest/user/login", json={"email": email, "password": password})
            if r.status_code == 200:
                token = r.json().get("authentication", {}).get("token")
                ctx.auth_context.bearer_token = token
            else:
                ctx.log_verdict("Login", r.status_code, "Auth Failed", "ERROR")
        except Exception as e:
            ctx.log_verdict("Login", "ERR", f"Exception: {e}", "ERROR")

    # ---------------------------------------------------------
    # B1: Admin Section (RBAC)
    # ---------------------------------------------------------
    try:
        r = ctx.client.get("/rest/admin/application-configuration")

        if role == "ADMIN":
            verdict = "NORMAL" if r.status_code == 200 else "ERR"
            details = "Admin access granted" if r.status_code == 200 else f"Admin blocked ({r.status_code})"
        else:
            verdict = "VULNERABLE" if r.status_code == 200 else "SECURE"
            details = "RBAC Bypass!" if r.status_code == 200 else "Access blocked"

        ctx.log_verdict("Missing Function Level Access Control", r.status_code, details, verdict)
    except Exception as e:
        ctx.log_verdict("Missing Function Level Access Control", "ERR", str(e), "ERR")


    # ---------------------------------------------------------
    # B2: Forged Feedback
    # ---------------------------------------------------------
    try:
        cid, ans = solve_captcha(ctx)
        if cid and ans:
            payload = {"comment": f"Audit {role}", "rating": 3, "captchaId": cid, "captcha": ans}
            r = ctx.client.post("/api/Feedbacks", json=payload)

            if role == "ADMIN":
                verdict = "NORMAL" if r.status_code in [200, 201] else "ERR"
            else:
                verdict = "SECURE" if r.status_code in [401, 403] else ("VULNERABLE" if r.status_code in [200, 201] else "UNKNOWN")

            ctx.log_verdict("Broken Access Control / IDOR (Impersonation)", r.status_code, "Done", verdict)
    except Exception:
        pass
