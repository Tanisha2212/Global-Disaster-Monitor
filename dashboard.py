# dashboard.py
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="🌍 Global Disaster Monitor - Google x MongoDB",
    page_icon="🌍",
    layout="wide"
)

# MongoDB connection

MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

client = MongoClient(MONGO_URI, tls=True, tlsInsecure=True)
db = client["gdelt"]
collection = db["disasters"]

# Load data with enhanced location parsing
@st.cache_data(ttl=600)
def load_disaster_data():
    disasters = list(collection.find({}).limit(2000))
    
    df_data = []
    for doc in disasters:
        coords = doc['location']['coordinates']
        location_parts = str(doc.get('location_name', '')).split(', ')
        
        # Parse location hierarchy
        country = location_parts[-1] if len(location_parts) > 0 else 'Unknown'
        state = location_parts[-2] if len(location_parts) > 1 else 'Unknown'
        city = location_parts[0] if len(location_parts) > 0 else 'Unknown'
        
        df_data.append({
            'lat': coords[1],
            'lon': coords[0],
            'disaster_type': doc['disaster_type'],
            'severity': doc['severity'],
            'location_name': doc['location_name'],
            'country': country,
            'state': state,
            'city': city,
            'date': doc['date'],
            'date_str': doc['date'].strftime('%Y-%m-%d'),
            'mentions': doc['mentions'],
            'topic_keywords': ', '.join(doc.get('topic_keywords', [])),
            'source_url': doc.get('source_url', ''),
            'actor1': str(doc.get('actor1', '')),
            'actor2': str(doc.get('actor2', '')),
            'goldstein': doc.get('goldstein', 0),
            'tone': doc.get('tone', 0),
            'cluster_id': doc.get('cluster_id', 'N/A')
        })
    
    return pd.DataFrame(df_data)

# Color mapping for disaster types
DISASTER_COLORS = {
    'earthquake': '#FF0000',
    'flood': '#0066CC', 
    'wildfire': '#FF6600',
    'storm': '#9900CC',
    'armed_conflict': '#CC0000',
    'explosion': '#FF3300',
    'accident': '#FFCC00',
    'other': '#666666'
}

def create_google_map_html(df_filtered):
    """Create Google Maps HTML with markers"""
    google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Prepare markers data
    markers_data = []
    for _, row in df_filtered.iterrows():
        color = DISASTER_COLORS.get(row['disaster_type'], '#666666')
        
        marker_data = {
            'lat': row['lat'],
            'lng': row['lon'],
            'title': f"{row['disaster_type'].title()}",
            'info': f"""
                <div style='max-width: 300px;'>
                    <h3 style='color: {color}; margin: 0;'>{row['disaster_type'].title()}</h3>
                    <p><strong>📍 Location:</strong> {row['location_name']}</p>
                    <p><strong>📅 Date:</strong> {row['date_str']}</p>
                    <p><strong>⚠️ Severity:</strong> {row['severity']}/5</p>
                    <p><strong>📰 Mentions:</strong> {row['mentions']}</p>
                    <p><strong>🤖 AI Topics:</strong> {row['topic_keywords']}</p>
                    {f"<p><a href='{row['source_url']}' target='_blank'>📰 Read News Source</a></p>" if row['source_url'] else ""}
                </div>
            """,
            'color': color,
            'size': int(row['severity']) * 3 + 5
        }
        markers_data.append(marker_data)
    
    if not google_api_key:
        return f"""
        <!DOCTYPE html>
        <html>
        <body>
            <div style="padding: 20px; text-align: center; background: #f0f0f0; height: 460px; display: flex; align-items: center; justify-content: center;">
                <div>
                    <h3>🗺️ Google Maps View</h3>
                    <p>Google Maps API key not found in environment variables</p>
                    <p>Add GOOGLE_MAPS_API_KEY to your .env file</p>
                    <p>Current markers: {len(markers_data)} disasters</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script async defer src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap"></script>
    </head>
    <body>
        <div id="map" style="height: 500px; width: 100%;"></div>
        
        <script>
            let map;
            let markers = {json.dumps(markers_data)};
            
            function initMap() {{
                map = new google.maps.Map(document.getElementById("map"), {{
                    zoom: 2,
                    center: {{ lat: 20, lng: 0 }},
                    mapTypeId: 'terrain'
                }});
                
                markers.forEach(function(markerData) {{
                    const marker = new google.maps.Marker({{
                        position: {{ lat: markerData.lat, lng: markerData.lng }},
                        map: map,
                        title: markerData.title,
                        icon: {{
                            path: google.maps.SymbolPath.CIRCLE,
                            fillColor: markerData.color,
                            fillOpacity: 0.8,
                            strokeColor: 'white',
                            strokeWeight: 2,
                            scale: markerData.size
                        }}
                    }});
                    
                    const infoWindow = new google.maps.InfoWindow({{
                        content: markerData.info
                    }});
                    
                    marker.addListener('click', function() {{
                        infoWindow.open(map, marker);
                    }});
                }});
            }}
        </script>
    </body>
    </html>
    """

# Main app
def main():
    # Header
    st.markdown("""
    # 🌍 Global Disaster Monitor
    ### Google Cloud × MongoDB Hackathon Project
    Real-time disaster tracking using GDELT data with AI analysis
    """)
    
    # Load data
    with st.spinner("🔄 Loading disaster data from MongoDB..."):
        df = load_disaster_data()
    
    if df.empty:
        st.error("❌ No data available. Please run the data collection script first.")
        return
    
    # Sidebar filters
    st.sidebar.markdown("## 🔍 Advanced Filters")
    
    # Date range filter
    st.sidebar.markdown("### 📅 Date Range")
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(max_date - timedelta(days=7), max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
    
    # Country filter
    countries = sorted(df['country'].unique().tolist())
    selected_countries = st.sidebar.multiselect(
        "🏳️ Select Countries",
        countries,
        default=countries[:10] if len(countries) > 10 else countries
    )
    
    # Disaster type filter
    df_country_filtered = df[df['country'].isin(selected_countries)]
    disaster_types = df_country_filtered['disaster_type'].unique().tolist()
    selected_types = st.sidebar.multiselect(
        "🔥 Select Disaster Types",
        disaster_types,
        default=disaster_types
    )
    
    # Severity filter
    severity_range = st.sidebar.slider(
        "⚠️ Severity Range (1=Low, 5=High)",
        min_value=1,
        max_value=5,
        value=(1, 5)
    )
    
    # Apply all filters
    df_filtered = df_country_filtered[
        (df_country_filtered['disaster_type'].isin(selected_types)) &
        (df_country_filtered['severity'] >= severity_range[0]) &
        (df_country_filtered['severity'] <= severity_range[1])
    ]
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🌍 Total Disasters", len(df_filtered))
    with col2:
        avg_severity = df_filtered['severity'].mean() if not df_filtered.empty else 0
        st.metric("📊 Avg Severity", f"{avg_severity:.1f}/5")
    with col3:
        total_mentions = df_filtered['mentions'].sum() if not df_filtered.empty else 0
        st.metric("📰 Total Mentions", f"{total_mentions:,}")
    with col4:
        unique_countries = df_filtered['country'].nunique() if not df_filtered.empty else 0
        st.metric("🏳️ Countries Affected", unique_countries)
    
    # Map section
    st.markdown("## 🗺️ Interactive Disaster Map")
    
    if not df_filtered.empty:
        google_map_html = create_google_map_html(df_filtered)
        st.components.v1.html(google_map_html, height=520)
        st.info(f"📍 Showing {len(df_filtered)} disasters on map")
    else:
        st.warning("⚠️ No disasters match your current filters")
    
    # Analytics charts
    st.markdown("## 📊 Disaster Analytics")
    
    if not df_filtered.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            type_counts = df_filtered['disaster_type'].value_counts()
            fig_pie = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="🔥 Disaster Types Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            severity_by_country = df_filtered.groupby('country')['severity'].mean().sort_values(ascending=False).head(10)
            fig_bar = px.bar(
                x=severity_by_country.values,
                y=severity_by_country.index,
                orientation='h',
                title="⚠️ Average Severity by Country"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **🚀 Powered by:** Google Maps API • MongoDB Atlas • AI Topic Modeling • GDELT Project
    """)

if __name__ == "__main__":
    main()