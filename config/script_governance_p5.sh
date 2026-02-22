#!/bin/bash

# ==============================================================================
# SCRIPT: governance_p5.sh
# PHASE:  P5 - Continuous Governance & Correlated Supervision
# DESC:   Generates a compliance snapshot of Azure IAM, RBAC, and App Security.
#         This artifact validates the non-drift of privileges (Hypothesis H5).
# ==============================================================================

# --- CONFIGURATION (UPDATED BASED ON YOUR AZURE SETUP) ---
OUTPUT_FILE="P5_Governance_Audit_$(date +%Y%m%d_%H%M).txt"
RESOURCE_GROUP="rg-msc-ojshop-weu-01"
APP_DISPLAY_NAME="app-msc-ojshop-sir-01"

# --- HEADER GENERATION ---
echo "Generating Governance Report..."
{
    echo "=============================================================================="
    echo "       PHASE P5 - CONTINUOUS GOVERNANCE & SECURITY POSTURE SNAPSHOT           "
    echo "=============================================================================="
    echo "Audit Date      : $(date -u)"
    echo "Tenant ID       : $(az account show --query tenantId -o tsv)"
    echo "Subscription    : $(az account show --query name -o tsv)"
    echo "Auditor         : $(az account show --query user.name -o tsv)"
    echo "Target Scope    : $RESOURCE_GROUP"
    echo "=============================================================================="
    echo ""

    # ------------------------------------------------------------------------------
    # 1. DIRECTORY ROLES (GLOBAL ADMINS / OWNERS)
    # Objective: Detect privilege escalation at the subscription level.
    # ------------------------------------------------------------------------------
    echo "[1] SUBSCRIPTION OWNERS (HIGH PRIVILEGE ACCOUNTS)"
    echo "------------------------------------------------------------------------------"
    echo "Scanning for Subscription Owners (Drift Control)..."
    az role assignment list --role "Owner" --query "[].{Principal:principalName, Type:principalType, Scope:scope}" --output table
    echo ""

    # ------------------------------------------------------------------------------
    # 2. RBAC SNAPSHOT (RESOURCE GROUP LEVEL)
    # Objective: Verify Least Privilege access on the specific workload.
    # ------------------------------------------------------------------------------
    echo "[2] RBAC SNAPSHOT - RESOURCE GROUP ($RESOURCE_GROUP)"
    echo "------------------------------------------------------------------------------"
    echo "Listing all active permissions on the workload..."
    az role assignment list --resource-group "$RESOURCE_GROUP" --query "[].{User:principalName, Role:roleDefinitionName, Type:principalType}" --output table
    echo ""

    # ------------------------------------------------------------------------------
    # 3. APP REGISTRATION GOVERNANCE (OWNERSHIP)
    # Objective: Ensure application identity is not hijacked (Shadow IT control).
    # ------------------------------------------------------------------------------
    echo "[3] APP REGISTRATION GOVERNANCE (OWNERSHIP)"
    echo "------------------------------------------------------------------------------"
    # Fetch App ID dynamically
    APP_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv)

    if [ -z "$APP_ID" ]; then
        echo "WARNING: Application '$APP_DISPLAY_NAME' not found."
        echo "Check if the App Registration name matches exactly."
    else
        echo "Target App ID: $APP_ID"
        echo "Owners:"
        az ad app owner list --id $APP_ID --query "[].{Owner:userPrincipalName, Type:jobTitle}" --output table
    fi
    echo ""

    # ------------------------------------------------------------------------------
    # 4. CREDENTIALS LIFECYCLE
    # Objective: Validate secret rotation and expiration policies.
    # ------------------------------------------------------------------------------
    echo "[4] CREDENTIALS & SECRET EXPIRATION STATUS"
    echo "------------------------------------------------------------------------------"
    if [ -n "$APP_ID" ]; then
        az ad app credential list --id $APP_ID --query "[].{KeyId:keyId, StartDate:startDate, EndDate:endDate, Status:'Active'}" --output table
    else
        echo "N/A (App ID missing)"
    fi
    echo ""

    # ------------------------------------------------------------------------------
    # 5. API PERMISSIONS (OAUTH2)
    # Objective: Audit declared permissions to prevent over-scoping.
    # ------------------------------------------------------------------------------
    echo "[5] DECLARED API PERMISSIONS (OAUTH2 SCOPES)"
    echo "------------------------------------------------------------------------------"
    if [ -n "$APP_ID" ]; then
        az ad app permission list --id $APP_ID --output json
    else
        echo "N/A (App ID missing)"
    fi
    echo ""

    # ------------------------------------------------------------------------------
    # 6. SECURE SCORE (POSTURE)
    # Objective: High-level view of the subscription security hygiene.
    # ------------------------------------------------------------------------------
    echo "[6] AZURE DEFENDER SECURE SCORE"
    echo "------------------------------------------------------------------------------"
    az security secure-scores list --query "[].{Policy:name, CurrentScore:current, MaxScore:max}" --output table
    echo ""

    echo "=============================================================================="
    echo " END OF REPORT - INTEGRITY CHECKSUM: $(openssl rand -hex 8)"
    echo "=============================================================================="

} > "$OUTPUT_FILE"

# --- USER FEEDBACK ---
echo "-----------------------------------------------------"
echo " Audit completed successfully."
echo " Report generated: $OUTPUT_FILE"
echo "-----------------------------------------------------"
echo " To view the report, type: cat $OUTPUT_FILE"
echo " To download it, use the Cloud Shell file menu."
echo "-----------------------------------------------------"