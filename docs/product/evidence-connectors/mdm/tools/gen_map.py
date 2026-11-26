"""Write ../device-evidence-map.csv: check -> artifact -> objectives -> control -> SOC 2 and ISO refs.

The rows below are the source of truth for the CSV and are kept in step with
04-checks-and-control-mapping.md sections 4.4 to 4.6.
Run: python gen_map.py
"""
import csv
from pathlib import Path

CONTROLS = {
    "EP-01": ("CC6.8 (full)", "A.8.1; A.8.7; A.8.16"),
    "EP-02": ("CC6.1; CC6.5; CC6.7", "A.7.9; A.7.10; A.8.1; A.8.24"),
    "EP-03": ("CC6.5; CC6.8", "A.6.7; A.7.9; A.8.1; A.8.19"),
    "EP-04": ("CC6.8; CC7.1", "A.8.8"),
    "EP-05": ("CC6.5", "A.5.11; A.7.9; A.7.14; A.8.1"),
    "EP-06": ("CC6.1", "A.7.7; A.8.1"),
    "EP-08": ("C1.2; CC6.5", "A.7.10; A.7.14"),
    "DM-19": ("", "A.5.14; A.7.10; A.8.12 (full)"),
    "HR-05": ("CC6.2; CC6.3", "A.5.11; A.6.5"),
    "HR-03": ("CC6.2; CC9.2", "A.5.11; A.8.30"),
    "LM-01": ("CC2.1; CC6.1", "A.5.9"),
}

DM = "device_management"
DMI = "device_management; identity_provider"
DMH = "device_management; hr_system"
HIST = "Verity daily history of baseline results"
LEAVER = "assigned_user_*; device.action; end date"

# check, status, capability, fields read, artifact, fill, objectives, control
ROWS = [
    ("devices.enrolled", "shipped", DM, "management_state; last_check_in_at; enrolment_channel; managed_by", "inventory-of-company-devices", "full", "EP-03.B", "EP-03"),
    ("devices.purchased_devices_enrolled", "new", DM, "device.purchase; serial_number; last_check_in_at", "inventory-of-company-devices", "partial", "EP-03.B", "EP-03"),
    ("devices.purchased_devices_enrolled", "new", DM, "device.purchase; serial_number", "asset-inventory", "partial", "LM-01.C", "LM-01"),
    ("devices.directory_devices_managed", "new", DMI, "device.directory; managed match", "inventory-of-company-devices", "partial", "EP-03.C", "EP-03"),
    ("devices.enrolled_before_issue", "new", DMH, "enrolled_at; first assignment; start date", "inventory-of-company-devices", "partial", "EP-03.B", "EP-03"),
    ("devices.enrolled_before_issue", "new", DMH, "enrolled_at; disk_encryption at first observation", "device-encryption-report", "partial", "EP-02.C", "EP-02"),
    ("devices.staff_have_managed_device", "round 1", DMI, "assigned_user_*; assignment_confidence", "inventory-of-company-devices", "partial", "EP-03.C", "EP-03"),
    ("devices.assigned_to_active_staff", "round 1", DMI, "assigned_user_*; assignment_confidence", "inventory-of-company-devices", "partial", "EP-03.C", "EP-03"),
    ("devices.assigned_to_active_staff", "round 1", DMI, "assigned_user_*", "asset-inventory", "partial", "LM-01.B", "LM-01"),
    ("devices.disk_encrypted", "shipped", DM, "disk_encryption; encryption_key_protected; passcode_present", "device-encryption-report", "full", "EP-02.B; EP-02.C", "EP-02"),
    ("devices.disk_encrypted", "shipped", DM, "disk_encryption", "device-baseline-report", "partial", "EP-03.D", "EP-03"),
    ("devices.recovery_key_escrowed", "round 1", DM, "recovery_key_escrowed; recovery_key_escrow_source", "device-encryption-report", "partial", "EP-02.B", "EP-02"),
    ("devices.drift_fixed_in_time", "new", DM, HIST, "device-encryption-report", "partial", "EP-02.C", "EP-02"),
    ("devices.drift_fixed_in_time", "new", DM, HIST, "device-baseline-report", "partial", "EP-03.D", "EP-03"),
    ("devices.drift_fixed_in_time", "new", DM, HIST, "patch-compliance-report", "partial", "EP-04.D", "EP-04"),
    ("devices.drift_fixed_in_time", "new", DM, HIST, "screen-lock-setting-report", "partial", "EP-06.D", "EP-06"),
    ("devices.screen_lock", "shipped", DM, "device.policy (passcode, screen_lock); idle_lock_seconds; passcode_present", "screen-lock-setting-report", "full", "EP-06.B; EP-06.C", "EP-06"),
    ("devices.screen_lock", "shipped", DM, "device.policy (passcode, screen_lock)", "screen-lock-setting-report", "partial", "EP-03.D", "EP-03"),
    ("devices.firewall_enabled", "round 1", DM, "firewall_on; firewall_profiles", "device-baseline-report", "partial", "EP-03.D", "EP-03"),
    ("devices.os_integrity", "new", DM, "os_integrity sub keys", "device-baseline-report", "partial", "EP-03.D", "EP-03"),
    ("devices.software_permitted", "new", DM, "installed_apps; managed_apps", "permitted-software-report", "full", "EP-03.E", "EP-03"),
    ("devices.byod_apps_protected", "new", DMI, "device.app_protection; device.directory", "personal-device-access-report", "partial", "EP-03.F (proposed)", "EP-03"),
    ("devices.os_current", "shipped", DM, "os_version; os_supplemental_version; security_patch_level; os_supported_until", "patch-compliance-report", "partial", "EP-04.C", "EP-04"),
    ("devices.os_current", "shipped", DM, "os_version; security_patch_level", "patch-compliance-report", "partial", "EP-03.D", "EP-03"),
    ("devices.browsers_current", "new", DM, "browser_versions", "patch-compliance-report", "partial", "EP-04.C", "EP-04"),
    ("devices.updates_automatic", "new", DM, "os_update_policy_assigned; device.policy (updates)", "patch-compliance-report", "partial", "EP-04.B", "EP-04"),
    ("devices.remote_wipe", "shipped", DM, "enrolment_channel; ownership; erase capability", "device-wipe-capability-report", "full", "EP-05.B", "EP-05"),
    ("devices.activation_lock_org_controlled", "new", DM, "activation_lock_type", "device-wipe-capability-report", "partial", "EP-05.B", "EP-05"),
    ("devices.wipes_confirmed", "round 1", DM, "device.action (confirmed_by, confirming_signal)", "wipe-confirmations-for-recovered-or-lost", "partial", "EP-05.D", "EP-05"),
    ("devices.leaver_devices_recovered", "round 1", DMH, LEAVER, "wipe-confirmations-for-recovered-or-lost", "partial", "EP-05.C", "EP-05"),
    ("devices.leaver_devices_recovered", "round 1", DMH, LEAVER, "completed-offboarding-records-for-leavers-in", "partial", "HR-05.E", "HR-05"),
    ("devices.leaver_devices_recovered", "round 1", DMH, LEAVER, "completed-offboarding-records-for-leavers-in", "partial", "HR-03.D (artifact to add, CC5)", "HR-03"),
    ("devices.removable_storage_restricted", "round 1", DM, "removable_storage_blocked; device.policy (removable_storage)", "leakage-prevention-and-sharing-settings-in", "partial", "DM-19.C", "DM-19"),
    ("devices.removed_have_disposal_record", "new", "device_management; verity_assets", "management_state history; Assets disposal record", "disposal-records-or-certificates", "partial", "EP-08.B", "EP-08"),
    ("endpoint.protection_active", "shipped", "endpoint_protection", "endpoint.sensor", "device-protection-agent-report", "full", "EP-01.B", "EP-01"),
    ("endpoint.coverage_complete", "round 1", "endpoint_protection; device_management", "endpoint.sensor; device match", "device-protection-agent-report", "partial", "EP-01.B", "EP-01"),
    ("endpoint.prevention_enabled", "round 1", "endpoint_protection", "endpoint.sensor policy", "device-protection-agent-report", "partial", "EP-01.B", "EP-01"),
    ("endpoint.servers_covered", "round 1", "endpoint_protection; verity_assets", "endpoint.sensor; asset match", "asset-inventory", "partial", "EP-01.B", "EP-01"),
    ("endpoint.detections_triaged", "round 1", "endpoint_protection", "endpoint.alert", "alerts-that-were-reviewed-and-acted", "partial", "EP-01.C", "EP-01"),
]


def main():
    out = Path(__file__).resolve().parent.parent / "device-evidence-map.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check", "status", "capability", "fields_read", "artifact", "fill",
                    "objectives", "control", "coverage", "soc2", "iso27001"])
        for check, status, cap, fields, art, fill, objs, ctl in ROWS:
            soc2, iso = CONTROLS[ctl]
            w.writerow([check, status, cap, fields, art, fill, objs, ctl, "partial", soc2, iso])
    checks = {r[0] for r in ROWS}
    assert len(checks) == 28, len(checks)  # 6 shipped + 11 round 1 + 11 new
    print(f"{len(ROWS)} rows, {len(checks)} checks -> {out}")


if __name__ == "__main__":
    main()
