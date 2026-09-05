import json
import sys
from pathlib import Path

# Allow importing from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.correlation import correlate_alerts


def load_alerts():
    data_path = PROJECT_ROOT / "data" / "alerts.json"

    with open(data_path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    alerts = load_alerts()

    incidents = correlate_alerts(alerts)

    print("\n" + "=" * 60)
    print("NEXUS ALERT CORRELATION TEST")
    print("=" * 60)

    print(f"\nTotal alerts: {len(alerts)}")
    print(f"Detected incidents: {len(incidents)}")

    for incident in incidents:

        print("\n" + "-" * 60)

        print(
            f"{incident['incident_id']} | "
            f"{incident['dominant_family']} | "
            f"{incident['highest_severity']}"
        )

        print(
            f"Alerts: {incident['alert_count']}"
        )

        print(
            f"Devices: {', '.join(incident['devices'])}"
        )

        print("Alert IDs:")

        for alert in incident["alerts"]:
            print(
                f"  - {alert['alert_id']} | "
                f"{alert['alert_type']} | "
                f"{alert['device_id']}"
            )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()