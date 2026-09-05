import json
import streamlit as st

from src.correlation import correlate_alerts
from src.runbook_retriever import search_runbooks
from src.gemini import analyze_incident


# -----------------------------
# Configuration
# -----------------------------
st.set_page_config(
    page_title="NEXUS | Network Incident Triage",
    page_icon="◈",
    layout="wide",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: #080b12;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .hero {
        padding: 22px 28px;
        border: 1px solid #252b38;
        border-radius: 16px;
        background: linear-gradient(135deg, #101622, #0b0f17);
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 38px;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 4px;
    }

    .hero-subtitle {
        color: #9ca7b8;
        font-size: 16px;
    }

    .metric-card {
        background: #10151f;
        border: 1px solid #252b38;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }

    .metric-number {
        font-size: 30px;
        font-weight: 800;
    }

    .metric-label {
        color: #8e99aa;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .incident-card {
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #252b38;
        background: #10151f;
        margin-bottom: 8px;
    }

    .critical {
        color: #ff5c5c;
        font-weight: 800;
    }

    .high {
        color: #ffad42;
        font-weight: 800;
    }

    .medium {
        color: #ffd166;
        font-weight: 800;
    }

    .low {
        color: #62d68a;
        font-weight: 800;
    }

    .unknown-box {
        border: 1px solid #ff5c5c;
        border-radius: 12px;
        padding: 18px;
        background: #241116;
        margin-top: 15px;
    }

    .success-box {
        border: 1px solid #62d68a;
        border-radius: 12px;
        padding: 18px;
        background: #101e17;
        margin-top: 15px;
    }

    .evidence {
        background: #111722;
        border-left: 4px solid #718096;
        padding: 10px 14px;
        margin: 7px 0;
        border-radius: 5px;
    }

    div[data-testid="stMetric"] {
        background: #10151f;
        border: 1px solid #252b38;
        padding: 12px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    with open("data/alerts.json", "r", encoding="utf-8") as f:
        alerts = json.load(f)

    with open("data/devices.json", "r", encoding="utf-8") as f:
        devices = json.load(f)

    incidents = correlate_alerts(alerts)

    return alerts, devices, incidents


alerts, devices, incidents = load_data()


# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">◈ NEXUS</div>
        <div class="hero-subtitle">
            Intelligent Network Incident Triage Assistant
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Metrics
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Network Alerts", len(alerts))

with col2:
    st.metric("Correlated Incidents", len(incidents))

with col3:
    critical_count = sum(
        1 for i in incidents if i["highest_severity"] == "critical"
    )
    st.metric("Critical Incidents", critical_count)

with col4:
    unknown_count = sum(
        1 for i in incidents if i["dominant_family"] == "unknown"
    )
    st.metric("Human Escalations", unknown_count)


st.divider()


# -----------------------------
# Incident list
# -----------------------------
st.subheader("Incident Overview")

for incident in incidents:
    severity = incident["highest_severity"]
    family = incident["dominant_family"]

    if severity == "critical":
        icon = "🔴"
    elif severity == "high":
        icon = "🟠"
    elif severity == "medium":
        icon = "🟡"
    else:
        icon = "🟢"

    st.markdown(
        f"""
        <div class="incident-card">
            {icon} <b>{incident['incident_id']}</b>
            &nbsp;&nbsp; 
            <span class="{severity}">{severity.upper()}</span>
            &nbsp;&nbsp; | &nbsp;&nbsp;
            {family.replace("_", " ").title()}
            &nbsp;&nbsp; | &nbsp;&nbsp;
            {incident['alert_count']} alerts
            &nbsp;&nbsp; | &nbsp;&nbsp;
            Devices: {", ".join(incident['devices'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


st.divider()


# -----------------------------
# Incident selection
# -----------------------------
st.subheader("AI Incident Analysis")

incident_options = [
    f"{i['incident_id']} — "
    f"{i['dominant_family'].replace('_', ' ').title()} — "
    f"{i['highest_severity'].upper()}"
    for i in incidents
]

selected_label = st.selectbox(
    "Select an incident to investigate",
    incident_options,
)

selected_index = incident_options.index(selected_label)
incident = incidents[selected_index]


# -----------------------------
# Incident details
# -----------------------------
left, right = st.columns([1, 1])

with left:
    st.markdown("### Incident Details")

    st.write(f"**Incident ID:** {incident['incident_id']}")
    st.write(f"**Severity:** {incident['highest_severity'].upper()}")
    st.write(f"**Alert Count:** {incident['alert_count']}")
    st.write(f"**Alert Family:** {incident['dominant_family'].replace('_', ' ').title()}")
    st.write(f"**Affected Devices:** {', '.join(incident['devices'])}")

    st.markdown("#### Correlated Alerts")

    for alert in incident["alerts"]:
        st.markdown(
            f"- `{alert['alert_id']}` — "
            f"`{alert['alert_type']}` — "
            f"`{alert['device_id']}` — "
            f"`{alert['severity']}`"
        )


# -----------------------------
# Runbook retrieval
# -----------------------------
family_queries = {
    "network_failure": "network link failure",
    "latency": "high latency",
    "authentication": "authentication failure",
    "packet_loss": "packet loss",
    "unknown": "",
}

query = family_queries.get(incident["dominant_family"], "")

if query:
    runbooks = search_runbooks(query, top_k=2)
else:
    runbooks = []


with right:
    st.markdown("### Retrieved Evidence")

    if runbooks:
        for rb in runbooks:
            st.markdown(
                f"""
                <div class="evidence">
                    <b>📄 {rb['runbook_id']}</b><br>
                    {rb['title']}<br>
                    <small>Relevance: {rb['score']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.warning("No matching runbook found.")


# -----------------------------
# Gemini Analysis
# -----------------------------
st.markdown("### NEXUS Reasoning")

if st.button("Analyze Incident with Gemini", type="primary"):

    with st.spinner("Gemini is analyzing incident evidence..."):

        try:
            result = analyze_incident(incident, runbooks)

            st.success("Gemini analysis completed.")

            # Summary
            st.markdown("#### Summary")
            st.write(result.get("summary", "No summary returned."))

            # Cause
            st.markdown("#### Probable Cause")
            st.write(result.get("probable_cause", "Insufficient evidence."))

            # Actions
            st.markdown("#### Recommended Actions")

            actions = result.get("recommended_actions", [])

            if actions:
                for action in actions:
                    st.markdown(f"✓ {action}")
            else:
                st.write("No recommended actions returned.")

            # Confidence
            confidence = result.get("confidence", "low").upper()
            st.markdown(f"**Confidence:** `{confidence}`")

            # Escalation
            escalation = result.get("escalation_required", False)

            if escalation:
                reason = result.get(
                    "escalation_reason",
                    "Insufficient evidence."
                )

                st.markdown(
                    f"""
                    <div class="unknown-box">
                        <h3>⚠ HUMAN ESCALATION REQUIRED</h3>
                        <b>Reason:</b><br>
                        {reason}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="success-box">
                        <h3>✓ INITIAL RESPONSE AVAILABLE</h3>
                        Evidence-supported troubleshooting actions
                        are available for the network engineer.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Evidence
            evidence = result.get("evidence", [])

            if evidence:
                st.markdown("#### Evidence Used")

                for item in evidence:
                    st.markdown(
                        f"""
                        <div class="evidence">
                            <b>{item.get('runbook_id', 'Unknown')}</b><br>
                            {item.get('claim', '')}<br>
                            <small>{item.get('source', '')}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        except Exception as e:
            st.error(f"Gemini analysis failed: {e}")


# -----------------------------
# Footer
# -----------------------------
st.divider()

st.caption(
    "NEXUS separates deterministic incident correlation from "
    "Gemini-based reasoning. Unknown cases are escalated instead "
    "of generating unsupported recommendations."
)