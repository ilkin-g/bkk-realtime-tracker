import streamlit as st
import duckdb
import yaml
import numpy as np
import pandas as pd

@st.cache_data(ttl=30)
def load_data(query):
    local_conn = duckdb.connect(config['database']['path'], read_only=True)

    try:
        local_conn.execute("INSTALL spatial; LOAD spatial;")
    except Exception:
        pass
        
    df = local_conn.execute(query).df()
    local_conn.close()
    return df

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

db_path = config["database"]["path"]
conn = duckdb.connect(db_path, read_only=True)

st.set_page_config(
    page_title="Budapest Tram Analytics",
    layout="wide"
)

st.sidebar.header("Filter Data")
time_option = st.sidebar.selectbox(
    "Select Time Range",
    ["Last 30 Minutes", "Last 4 Hours", "Last 24 Hours", "All Time"]
)

def get_time_filter_sql(table_name, time_col="timestamp"):
    base_subquery = f"(SELECT MAX({time_col}) FROM {table_name})"
    
    if time_option == "Last 30 Minutes":
        return f"WHERE {time_col} >= {base_subquery} - 1800"
    elif time_option == "Last 4 Hours":
        return f"WHERE {time_col} >= {base_subquery} - 14400"
    elif time_option == "Last 24 Hours":
        return f"WHERE {time_col} >= {base_subquery} - 86400"
    else:
        return ""

s_tab, h_tab, p_tab = st.tabs(["Performance (Speed)", "Reliability (Headway)", "Punctuality (Delay)"])

with s_tab:
    st.header("Real-Time Network Speed")

    time_filter = get_time_filter_sql("view_tram_movement")
    
    if time_filter:
        query = f"SELECT * FROM view_tram_movement {time_filter} AND prev_lat IS NOT NULL"
    else:
        query = "SELECT * FROM view_tram_movement WHERE prev_lat IS NOT NULL"
    
    speed_df = load_data(query)

    if not speed_df.empty:
        active_trams = speed_df[
            (speed_df["speed_kmh"] > 1) & 
            (speed_df["speed_kmh"] < 80)
        ]

        avg_speed = active_trams["speed_kmh"].mean()
        st.metric("Average Network Speed", f"{avg_speed:.1f} km/h")

        st.subheader("Traffic Heatmap")
        
        st.caption("🔴 Stuck (<10km/h) | 🟡 Moving (10-25km/h) | 🟢 Fast (>25km/h)")
        
        map_data = pd.DataFrame({
            'lat': active_trams['lat'],
            'lon': active_trams['lon'],
            'color': active_trams['speed_kmh'].map(
                lambda x: '#ff0000' if x <= 10 else ('#ffff00' if x <= 25 else '#00ff00')
            )
        })
                
        st.map(map_data, color="color")
    
    else:
        st.warning("Not enough data yet. Wait for a few batch loops in main.py!")

with h_tab:
    st.header("Schedule Reliability")
    time_filter = get_time_filter_sql("view_tram_headway", time_col="arrival_time")
    
    if time_filter:
        query = f"SELECT * FROM view_tram_headway {time_filter} AND headway_min > 0.5 AND headway_min < 60"
    else:
        query = "SELECT * FROM view_tram_headway WHERE headway_min > 0.5 AND headway_min < 60"

    df_headway = load_data(query)

    if not df_headway.empty:
        col1, col2 = st.columns(2)
        
        avg_wait = df_headway["headway_min"].mean()

        bunching_events = len(df_headway[df_headway["headway_min"] < 2.0])

        col1.metric("Avg Wait Time", f"{avg_wait:.1f} min")
        col2.metric("Bunching Events", bunching_events, delta_color="inverse")
        st.subheader("Distribution of Wait Times")
        st.caption("How long do passengers actually wait?")
        
        hist_data = df_headway["headway_min"].round(1).value_counts().sort_index()
        
        st.bar_chart(hist_data)
    
    else:
        st.info("Gathering data... wait for the next batch update.")

with p_tab:
    st.header("On-Time Performance (OTP)")

    query = """
        SELECT * FROM view_schedule_adherence 
        WHERE delay_minutes > -30 AND delay_minutes < 30
    """
    df_delay = load_data(query)

    if not df_delay.empty:
        avg_delay = df_delay["delay_minutes"].mean()
        
        late_count = len(df_delay[df_delay["delay_minutes"] > 1.5]) 
        early_count = len(df_delay[df_delay["delay_minutes"] < -1.0])
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Avg Delay", f"{avg_delay:.1f} min", 
                    delta="-Early" if avg_delay < 0 else "Late", delta_color="inverse")
        col2.metric("Late Arrivals (>1.5m)", late_count)
        col3.metric("Early Arrivals (<-1m)", early_count)

        st.subheader("Lateness Distribution")
        st.caption("Positive = Late | Negative = Early")
        
        hist_data = ((df_delay["delay_minutes"] * 2).round() / 2).value_counts().sort_index()
        st.bar_chart(hist_data)
        
    else:
        st.info("Gathering data... The Matchmaker is looking for pairs! (Wait for a few tram updates)")
    