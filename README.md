# 🛡️ Experimental IAM Orchestrator - Research Artefact

**Author:** IRINA Stephanie  
**Programme:** MSc Cyber Security, University of Essex  
**Supervisor:** Dr Anupam Mazumdar  

---

## 1. Purpose of the Repository

This repository constitutes the experimental artefact supporting the dissertation entitled:  
> **"Study of the impact of IAM mechanisms application on the overall security posture of a vulnerable cloud environment."**

It contains the execution framework, configuration files, and attack scenarios used to empirically evaluate how Identity and Access Management (IAM) mechanisms influence the security posture of a cloud-based system. 

The environment under study combines:
* A **Microsoft Azure API Management (APIM)** gateway acting as a policy enforcement point.
* An intentionally vulnerable backend application (**OWASP Juice Shop**).
* A set of IAM mechanisms progressively introduced following a controlled experimental design.



*Note: The objective is not to demonstrate isolated vulnerabilities, but to observe measurable variations in access control decisions under successive IAM configurations.*

---

## 2. Conceptual Positioning of the Artefact

This artefact must be understood as part of a **controlled experimental protocol**, not as a standalone software product or offensive security tool.

The experimental logic follows a phase-based progression (Phase P0 to P5) relying on a strict **One-Factor-at-a-Time** methodology:
1. **The Python execution framework remains strictly invariant.**
2. **Only the IAM configuration in Azure is modified** between experimental runs.
3. **Observed variations are causally attributable** to the IAM mechanisms deployed on the cloud gateway.

This approach ensures the isolation of variables, the reproducibility of results, and the validity of causal interpretations.

---

## 3. Repository Structure

The repository is organised to reflect the separation between configuration, execution, and observation:

```text
├── config/
│   ├── config.yaml          # Global configuration (Targets, Personas: Admin, Standard, Guest)
│   └── apim_config_p*.xml   # IAM policy definitions applied manually in Azure APIM per phase
├── run/
│   ├── runner.py            # Orchestrates scenario execution and evidence collection
│   ├── auth_runner.py       # Manages interactive MFA authentication flows
│   └── attempt_record.py    # Handles data structure and cryptographic hashing
├── scenarios/
│   ├── scenario1.py         # Vertical Access Control & Race Condition
│   ├── scenario2.py         # BOLA & Function Level Access Control
│   ├── scenario3.py         # Credential Stuffing & OSINT Info Disclosure
│   ├── scenario4.py         # SSRF & SQL Injection
│   └── scenario5.py         # Stored Cross-Site Scripting (XSS)
└── runs/                    # (Auto-generated) Stores all artefacts resulting from execution
```

---

## 4. Evidence Generation and Data Integrity
The `runs/` directory contains the actual results discussed in the dissertation. It is composed of **15 individual folders**, representing the records of each experimental phase (P0, P1, P2, P3, P4) executed three times (n=3) to ensure the consistency of the observations.
Each execution produces a structured set of artefacts stored in a timestamped `runs/` directory, ensuring full traceability and reproducibility of the experiment.

* **Observations (`observations_*.csv`)**
  Aggregated results representing the security verdict for each scenario and persona (e.g., `VULNERABLE`, `SECURE`, `NORMAL`).

* **Attempts (`attempts_*.csv`)**
  Structured dataset containing all executed actions, enabling quantitative analysis such as the calculation of the Attack Success Ratio (ASR).

* **Raw logs (`attempts_*.jsonl`)**
  Detailed forensic records of each HTTP request and response, preserving the full execution trace.

---

## 5. Experimental Execution Protocol

The execution of this framework must strictly follow the experimental design.

### 5.1 Prerequisites

* Python 3.8 or higher installed
* Dependencies installed via:

  ```bash
  pip install -r requirements.txt
  ```

* Initialisation of the token cache file:

  ```bash
  
  touch token_cache.bin

### 5.2 Phase P0 - Vulnerable Baseline

This phase represents a system without structured IAM controls. 

* **Execution:**

  ```bash
  python -c "from run.runner import run_audit; run_audit()"
  ```

The resulting artefacts establish the reference state of maximal exposure.

### 5.3 Phases P1 to P4 - Progressive IAM Enforcement

From Phase P1 onwards, structured IAM controls are introduced (RBAC, MFA, token validation).

**Step 1 - Azure Configuration**
* Import the corresponding IAM policy (e.g., `config/apim_config_p1.xml`) into Azure API Management.
* Each phase corresponds to a frozen configuration state.

**Step 2 - Authentication and Token Acquisition**

  ```bash
  python -c "from run.auth_runner import interactive_login; interactive_login()"
  ```
* This requires interactive login and MFA validation.
* Tokens are stored in `token_cache.bin`.

**Step 3 - Constrained Execution**

  ```bash
  python -c "from run.runner import run_audit; run_audit()"
  ```
* The framework executes invariant scenarios under IAM constraints and records all decisions.
* Repeat the full process for each phase.

---

## 6. Ethical and Legal Considerations

This repository has been developed exclusively for academic research purposes.
The scenarios include vulnerability audit techniques:

* SQL Injection
* Server-Side Request Forgery (SSRF)
* Broken Access Control (BOLA)
* Cross-Site Scripting (XSS)

All experiments must be executed only within the designated laboratory environment (private Azure tenant and OWASP Juice Shop). Any use against external systems is strictly prohibited.

---

## 7. Relation to the Dissertation

This artefact operationalises the experimental design and provides the empirical basis for the results analysis.
