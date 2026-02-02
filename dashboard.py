import streamlit as st
import pydeck as pdk
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
        st.caption("🔴 Stuck (<10km/h) | 🟡 Moving | 🟢 Fast (>25km/h)")
        
        def get_color(speed):
            if speed <= 10: return [255, 0, 0, 160]
            if speed <= 25: return [255, 255, 0, 160]
            return [0, 255, 0, 160]
            
        map_df = active_trams.copy()
        map_df['color'] = map_df['speed_kmh'].apply(get_color)

        view_state = pdk.ViewState(
            latitude=47.4979, 
            longitude=19.0402, 
            zoom=12, 
            pitch=0
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_radius=60,
            get_fill_color='color',
            pickable=True,
            opacity=0.8,
            stroked=True,
            filled=True
        )

        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "Route: {route_id}\nSpeed: {speed_kmh} km/h"},
            map_style=pdk.map_styles.CARTO_DARK
        )
        
        st.pydeck_chart(r)
    
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
        
        headway_data = df_headway[df_headway["headway_min"] < 20]["headway_min"]
        
        if not headway_data.empty:
            min_val = 0
            max_val = headway_data.max()
            
            if pd.isna(max_val) or max_val == 0:
                 st.info("Gathering more data for the curve...")
            else:
                bins = np.arange(min_val, max_val + 0.2, 0.1)
                
                counts, bin_edges = np.histogram(headway_data, bins=bins)
                hist_df = pd.DataFrame({"Arrivals": counts}, index=np.round(bin_edges[:-1], 1))
                
                st.area_chart(hist_df, color="#00aabb")
        else:
             st.info("No wait time data available for this range.")

        st.markdown("---")
        st.subheader("The Worst Stops")
        st.caption("Stops with the highest frequency of tram bunching (Headway < 2 min)")
        
        worst_stops_query = f"""
            SELECT 
                s.stop_name, 
                COUNT(*) as total_arrivals,
                COUNT(CASE WHEN v.headway_min < 2 THEN 1 END) as bunching_events,
                ROUND(AVG(v.headway_min), 1) as avg_wait_min
            FROM view_tram_headway v
            JOIN stops s ON v.stop_id = s.stop_id
            {time_filter}
            AND s.stop_name NOT LIKE '%Széll Kálmán%' 
            AND s.stop_name NOT LIKE '%Móricz Zsigmond%'
            AND s.stop_name NOT LIKE '%Újbuda-központ%'
            GROUP BY s.stop_name
            HAVING total_arrivals > 5
            ORDER BY bunching_events DESC
            LIMIT 5
        """
        
        worst_df = load_data(worst_stops_query)
        if not worst_df.empty:
            worst_df["avg_wait_min"] = worst_df["avg_wait_min"].apply(lambda x: f"{x:.1f}")
            worst_df.columns = ["Stop Name", "Total Arrivals", "Bunching Events", "Avg Wait (min)"]
            st.table(worst_df)
        else:
            st.info("Not enough data yet to identify Black Holes.")
    
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
        late_mask = df_delay["delay_minutes"] > 0
        avg_late = df_delay.loc[late_mask, "delay_minutes"].mean() if late_mask.any() else 0.0
        
        early_mask = df_delay["delay_minutes"] < 0
        avg_early = df_delay.loc[early_mask, "delay_minutes"].mean() if early_mask.any() else 0.0
        
        late_count = len(df_delay[df_delay["delay_minutes"] > 1.5]) 
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Lateness", f"+{avg_late:.1f} min", "Late", delta_color="inverse")
        col2.metric("Avg Earliness", f"{avg_early:.1f} min", "Early", delta_color="off") 
        col3.metric("Severe Delays (>1.5m)", late_count, "Events", delta_color="inverse")

        st.subheader("Lateness Distribution")
        st.caption("Positive = Late | Negative = Early")
        
        if not df_delay["delay_minutes"].empty:
            min_val = df_delay["delay_minutes"].min()
            max_val = df_delay["delay_minutes"].max()
            
            if pd.isna(min_val) or pd.isna(max_val):
                 st.info("Gathering data points...")
            else:
                bins = np.arange(np.floor(min_val), np.ceil(max_val) + 0.1, 0.1)
                
                counts, bin_edges = np.histogram(df_delay["delay_minutes"], bins=bins)
                hist_df = pd.DataFrame({"Trams": counts}, index=np.round(bin_edges[:-1], 1))
                
                st.area_chart(hist_df, color="#3366cc")
        else:
            st.info("No delay data available to plot.")
        
    else:
        st.info("Gathering data... The Matchmaker is looking for pairs! (Wait for a few tram updates)")