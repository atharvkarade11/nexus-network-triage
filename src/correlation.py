from datetime import datetime
from collections import Counter


# ---------------------------------------------------------
# Canonical alert classification
# ---------------------------------------------------------

ALERT_FAMILY = {
    "link_down": "network_failure",
    "device_unreachable": "network_failure",

    "packet_loss": "packet_loss",
    "interface_errors": "packet_loss",
    "link_flapping": "packet_loss",

    "latency_high": "latency",
    "timeout": "latency",

    "authentication_failure": "authentication",
    "account_lockout": "authentication",

    # No known runbook -> human escalation
    "unknown_signal": "unknown",
    "cpu_high": "unknown",
    "connection_slow": "unknown",
    "connection_timeout": "unknown"
}


SEVERITY_SCORE = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}


NETWORK_FAMILIES = {
    "network_failure",
    "packet_loss",
    "latency"
}


def parse_timestamp(timestamp):
    return datetime.fromisoformat(timestamp)


def get_alert_family(alert_type):
    return ALERT_FAMILY.get(alert_type, "unknown")


def load_topology(path="data/topology.json"):
    import json

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    connections = set()

    for device_a, device_b in data.get("connections", []):
        connections.add((device_a, device_b))
        connections.add((device_b, device_a))

    return connections


def are_connected(device_a, device_b, topology):
    return (device_a, device_b) in topology


def time_difference(alert_a, alert_b):
    time_a = parse_timestamp(alert_a["timestamp"])
    time_b = parse_timestamp(alert_b["timestamp"])

    return abs((time_a - time_b).total_seconds())


def correlation_score(alert_a, alert_b, topology, window_seconds=30):
    difference = time_difference(alert_a, alert_b)

    if difference > window_seconds:
        return 0

    family_a = get_alert_family(alert_a["alert_type"])
    family_b = get_alert_family(alert_b["alert_type"])

    score = 0

    # Same device is the strongest signal
    if alert_a["device_id"] == alert_b["device_id"]:
        score += 50

    # Same alert family
    if family_a == family_b:
        score += 35

    # Connected network devices
    if are_connected(
        alert_a["device_id"],
        alert_b["device_id"],
        topology
    ):
        score += 40

    # Different but related network symptoms
    if (
        family_a in NETWORK_FAMILIES
        and family_b in NETWORK_FAMILIES
    ):
        score += 20

    # Very close timestamps
    if difference <= 10:
        score += 20
    elif difference <= 30:
        score += 10

    return score


def should_correlate(
    alert_a,
    alert_b,
    topology,
    window_seconds=30
):
    score = correlation_score(
        alert_a,
        alert_b,
        topology,
        window_seconds
    )

    family_a = get_alert_family(alert_a["alert_type"])
    family_b = get_alert_family(alert_b["alert_type"])

    # Same device:
    # allow related alerts, including unknown alerts.
    if alert_a["device_id"] == alert_b["device_id"]:
        return score >= 70

    # Different devices:
    # only network-related incidents can cross devices.
    if (
        family_a in NETWORK_FAMILIES
        and family_b in NETWORK_FAMILIES
    ):
        return score >= 60

    return False


def correlate_alerts(
    alerts,
    window_seconds=30,
    topology_path="data/topology.json"
):
    if not alerts:
        return []

    topology = load_topology(topology_path)

    sorted_alerts = sorted(
        alerts,
        key=lambda alert: parse_timestamp(alert["timestamp"])
    )

    visited = set()
    incident_groups = []

    for alert in sorted_alerts:

        if alert["alert_id"] in visited:
            continue

        group = [alert]
        visited.add(alert["alert_id"])

        changed = True

        # Expand the group until no new related alerts are found.
        while changed:
            changed = False

            for candidate in sorted_alerts:

                if candidate["alert_id"] in visited:
                    continue

                if any(
                    should_correlate(
                        existing,
                        candidate,
                        topology,
                        window_seconds
                    )
                    for existing in group
                ):
                    group.append(candidate)
                    visited.add(candidate["alert_id"])
                    changed = True

        incident_groups.append(group)

    incidents = []

    for number, group in enumerate(
        incident_groups,
        start=1
    ):
        highest_severity = max(
            group,
            key=lambda alert: SEVERITY_SCORE.get(
                alert["severity"],
                0
            )
        )

        families = [
            get_alert_family(alert["alert_type"])
            for alert in group
        ]

        family_counts = Counter(families)

        dominant_family = family_counts.most_common(1)[0][0]

        incidents.append({
            "incident_id": f"INC-{1000 + number}",
            "alert_count": len(group),
            "alerts": group,
            "dominant_family": dominant_family,
            "highest_severity": highest_severity["severity"],
            "devices": sorted(
                list(
                    set(
                        alert["device_id"]
                        for alert in group
                    )
                )
            )
        })

    return incidents