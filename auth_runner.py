from run.config_loader import load_runner_config
from run.auth_manager import AzureAuthManager
import sys


def interactive_login():
    print("==========================================")
    print("   OPENING AZURE SESSION  (MFA)       ")
    print("==========================================")

    cfg = load_runner_config("config/config.yaml")

    if not hasattr(cfg, 'azure_client_id') or not cfg.azure_client_id:
        print("⚠ ErrOr: 'azure_client_id' missing in config.yaml")
        print("Configure App Registration.")
        return

    manager = AzureAuthManager(cfg)

    for persona in cfg.personas:
        azure_email = getattr(persona, 'azure_email', None)

        if not azure_email:
            print(f"\n Pass: {persona.persona_id} (No Azure account)")
            continue

        print(f"\n Persona/ User : {persona.persona_id}")
        print(f"    Azure account : {azure_email}")

        choice = input("   > MFA Login ? [O/n] ")
        if choice.lower() in ['', 'o', 'y', 'oui']:
            manager.login_interactive(persona.persona_id, azure_email)
        else:
            print("   Ignored.")

    print("\n Ended. Tokens are in cache.")
    print("Launch runner : python -c \"from run.runner import run_audit; run_audit()\"")


if __name__ == "__main__":
    interactive_login()