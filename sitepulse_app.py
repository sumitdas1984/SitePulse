"""SitePulse Streamlit Dashboard - Professional Site Reliability Monitor"""

import os
import time
from datetime import datetime, timedelta
import streamlit as st
import httpx
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# --- CONFIGURATION ---
st.set_page_config(
    page_title="SitePulse | Dev-Ops Monitor",
    page_icon="📡",
    layout="wide",
)

# Custom CSS for modern UI (from mockup)
st.markdown("""
    <style>
    .status-dot {
        height: 12px;
        width: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .dot-online { background-color: #10b981; box-shadow: 0 0 8px #10b981; }
    .dot-offline { background-color: #ef4444; box-shadow: 0 0 8px #ef4444; }
    .dot-warning { background-color: #f59e0b; box-shadow: 0 0 8px #f59e0b; }

    .metric-card {
        background-color: white;
        padding: 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #edf2f7;
    }
    .heatmap-cell {
        width: 4px;
        height: 24px;
        border-radius: 2px;
        display: inline-block;
        margin: 1px;
    }
    </style>
    """, unsafe_allow_html=True)


# --- API HELPER FUNCTIONS ---
def api_get(endpoint: str):
    """Make GET request to API."""
    try:
        response = httpx.get(f"{API_BASE_URL}{endpoint}", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_post(endpoint: str, data: dict):
    """Make POST request to API."""
    try:
        response = httpx.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_delete(endpoint: str):
    """Make DELETE request to API."""
    try:
        response = httpx.delete(f"{API_BASE_URL}{endpoint}", timeout=10.0)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"API Error: {e}")
        return False


# --- UI HELPER FUNCTIONS ---
def render_heatmap(cells):
    """Renders a row of colored blocks representing uptime history (last 90 hours)."""
    html = '<div style="display: flex; gap: 1px;">'

    # Take last 90 cells for display
    display_cells = cells[-90:] if len(cells) > 90 else cells

    for cell in display_cells:
        status = cell.get("status", "no_data")
        if status == "up":
            color = "#10b981"
        elif status == "degraded":
            color = "#f59e0b"
        elif status == "down":
            color = "#ef4444"
        else:  # no_data
            color = "#e2e8f0"

        html += f'<div class="heatmap-cell" style="background-color: {color};"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def get_monitor_status(monitor):
    """Determine monitor status: online, warning, or offline."""
    failures = monitor.get("consecutive_failures", 0)
    threshold = monitor.get("failure_threshold", 3)

    if failures >= threshold:
        return "offline"
    elif failures > 0:
        return "warning"
    else:
        return "online"


# --- PAGE FUNCTIONS ---
def show_dashboard():
    """Dashboard page showing all monitors and their status."""
    st.header("Service Pulse Dashboard")

    # Get all monitors
    monitors = api_get("/monitors")

    if not monitors:
        st.info("No monitors configured. Go to the Management page to add one.")
        return

    # 1. Global Stats
    total_services = len(monitors)
    healthy = sum(1 for m in monitors if get_monitor_status(m) == "online")

    # Calculate average latency from recent stats
    total_latency = 0
    latency_count = 0
    incidents_24h = 0

    for monitor in monitors:
        stats = api_get(f"/monitors/{monitor['id']}/stats?window_hours=24")
        if stats and stats.get("avg_latency_ms"):
            total_latency += stats["avg_latency_ms"]
            latency_count += 1
        if monitor.get("consecutive_failures", 0) > 0:
            incidents_24h += 1

    avg_latency = int(total_latency / latency_count) if latency_count > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Services", total_services)
    with m2:
        st.metric("Healthy", healthy)
    with m3:
        st.metric("Avg Latency", f"{avg_latency}ms")
    with m4:
        delta_color = "inverse" if incidents_24h > 0 else "normal"
        st.metric("Incidents (24h)", incidents_24h, delta="Major" if incidents_24h > 0 else None)

    st.markdown("---")

    # 2. Service List
    for monitor in monitors:
        stats = api_get(f"/monitors/{monitor['id']}/stats?window_hours=24")
        heatmap_data = api_get(f"/monitors/{monitor['id']}/heatmap")

        status = get_monitor_status(monitor)
        uptime = stats.get("uptime_pct", 0) if stats else 0
        latency = int(stats.get("avg_latency_ms", 0)) if stats else 0

        with st.container(border=True):
            col_info, col_history, col_action = st.columns([1.5, 3, 0.5])

            with col_info:
                dot_class = f"dot-{status}"
                st.markdown(f'### <span class="status-dot {dot_class}"></span> {monitor["name"]}', unsafe_allow_html=True)
                st.caption(monitor['url'])

                # Small metrics row
                sub1, sub2 = st.columns(2)
                sub1.write(f"**Uptime:** {uptime:.2f}%")
                sub2.write(f"**Latency:** {latency}ms")

            with col_history:
                st.write("**90 Day Availability**")
                if heatmap_data and heatmap_data.get("cells"):
                    render_heatmap(heatmap_data["cells"])
                    st.caption("Each bar represents 1 hour of aggregated availability data.")
                else:
                    st.caption("No data available yet")

            with col_action:
                st.button("⚙️", key=f"edit_{monitor['id']}")
                st.button("📊", key=f"stat_{monitor['id']}")


def show_management():
    """Management page for configuring monitors."""
    st.header("Configure Monitoring Targets")

    with st.expander("➕ Add New Service", expanded=True):
        with st.form("new_service"):
            col_a, col_b = st.columns(2)
            name = col_a.text_input("Service Name", placeholder="My API")
            url = col_b.text_input("Target URL", placeholder="https://api.example.com/health")

            col_c, col_d = st.columns(2)
            interval = col_c.select_slider("Check Interval", options=[1, 5, 10, 15, 30, 60], value=5, help="Minutes between checks")
            alert_email = col_d.text_input("Alert Email", placeholder="devops@company.com")

            submitted = st.form_submit_button("Initialize Monitor", use_container_width=True)

            if submitted:
                monitor_data = {
                    "name": name,
                    "url": url,
                    "interval_minutes": interval,
                    "failure_threshold": 3,
                }

                if alert_email:
                    monitor_data["alert_email"] = alert_email

                result = api_post("/monitors", monitor_data)

                if result:
                    st.success(f"SitePulse is now monitoring {url} every {interval} minutes.")
                    time.sleep(1)
                    st.rerun()

    st.subheader("Existing Targets")
    monitors = api_get("/monitors")

    if monitors:
        # Build dataframe
        monitor_list = []
        for m in monitors:
            stats = api_get(f"/monitors/{m['id']}/stats?window_hours=24")
            uptime = stats.get("uptime_pct", 0) if stats else 0

            monitor_list.append({
                "name": m["name"],
                "url": m["url"],
                "status": get_monitor_status(m),
                "uptime": f"{uptime:.4f}"
            })

        df = pd.DataFrame(monitor_list)
        st.table(df)
    else:
        st.info("No monitors configured yet.")


def show_analytics():
    """Analytics page showing system-wide trends and incidents."""
    st.header("System-Wide Latency Trends")

    # Latency chart
    latency_data = api_get("/analytics/latency")

    if latency_data:
        df = pd.DataFrame(latency_data)
        df["hour"] = pd.to_datetime(df["hour"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["hour"],
            y=df["avg_latency_ms"],
            fill='tozeroy',
            line_color='#3b82f6',
            name='Latency (ms)'
        ))
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Time",
            yaxis_title="Latency (ms)",
            template="plotly_white",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No latency data available yet.")

    st.subheader("Incident Log")
    incidents = api_get("/analytics/incidents")

    if incidents:
        incident_list = []
        for inc in incidents:
            incident_list.append({
                "Timestamp": inc["timestamp"],
                "Service": inc["monitor_name"],
                "Event": inc["failure_reason"] or "Unknown",
                "Severity": inc["severity"]
            })
        st.table(incident_list)
    else:
        st.success("No incidents in the last 7 days!")


# --- MAIN APP ---
def main():
    # Sidebar Navigation
    with st.sidebar:
        st.title("📡 SitePulse")
        st.caption("Professional Site Reliability Monitor")
        st.markdown("---")

        page = st.radio("Navigation", ["Dashboard", "Management", "Analytics"])

        st.markdown("---")
        st.write("### System Status")

        # Check API health
        try:
            api_status = api_get("/")
            if api_status and api_status.get("status") == "ok":
                st.success("Internal Monitor: **ACTIVE**")
            else:
                st.error("Internal Monitor: **ERROR**")
        except:
            st.error("API: **OFFLINE**")

        # Auto-refresh countdown
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()

        time_since_refresh = int(time.time() - st.session_state.last_refresh)
        time_until_refresh = max(0, 45 - time_since_refresh)

        st.info(f"Next Sync: In {time_until_refresh}s")

        if time_until_refresh == 0:
            st.session_state.last_refresh = time.time()
            st.rerun()

    # Route to correct page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Management":
        show_management()
    else:
        show_analytics()


if __name__ == "__main__":
    main()
