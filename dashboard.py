import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from datahandler import DataHandler
from config import Config
from report_generator import generate_report

def create_google_map_html(df_filtered):
    markers_data = []
    for _, row in df_filtered.iterrows():
        color = Config.DISASTER_COLORS.get(row['disaster_type'], '#666666')
        
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
    
    if not Config.GOOGLE_MAPS_API_KEY:
        return f"""
        <div style="padding: 20px; text-align: center; background: #f0f0f0; height: 460px; display: flex; align-items: center; justify-content: center;">
            <div>
                <h3>🗺️ Google Maps View</h3>
                <p>Google Maps API key not found</p>
                <p>Add GOOGLE_MAPS_API_KEY to your .env file</p>
                <p>Current markers: {len(markers_data)} disasters</p>
            </div>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script async defer src="https://maps.googleapis.com/maps/api/js?key={Config.GOOGLE_MAPS_API_KEY}&callback=initMap"></script>
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

def create_cluster_map(df_filtered):
    fig = px.scatter_mapbox(
        df_filtered,
        lat='lat',
        lon='lon',
        color='disaster_type',
        color_discrete_map=Config.DISASTER_COLORS,
        zoom=1,
        height=500,
        title="Cluster Map View",
        hover_data=['location_name', 'severity', 'date_str']
    )
    fig.update_layout(mapbox_style="open-street-map")
    return fig

def create_correlation_matrix(df_filtered):
    corr_matrix = data_handler.get_correlation_matrix(df_filtered)
    fig = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='RdBu',
        title="Feature Correlation Matrix"
    )
    return fig

def create_story_mode(df_stories):
    stories_html = ""
    for _, story in df_stories.iterrows():
        stories_html += f"""
        <div style="border-left: 3px solid {Config.DISASTER_COLORS.get(story['disaster_type'], '#666666')}; 
                    padding-left: 10px; margin-bottom: 20px;">
            <h4>{story['disaster_type'].title()} in {story['country']}</h4>
            <p><strong>📅 Date:</strong> {story['date_str']}</p>
            <p><strong>⚠️ Severity:</strong> {story['severity']}/5</p>
            <p><strong>📰 Mentions:</strong> {story['mentions']}</p>
            <p>{story['topic_keywords']}</p>
        </div>
        """
    
    return f"""
    <div style="display: flex;">
        <div style="flex: 1;">
            {stories_html}
        </div>
        <div style="width: 100px; text-align: center;">
            <div style="font-size: 48px;">{Config.STORY_MODE_ICON}</div>
            <p style="font-size: 12px; margin-top: 0;">Analyst Summary</p>
        </div>
    </div>
    """

def create_news_feed(news_items):
    news_html = ""
    for item in news_items:
        news_html += f"""
        <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
            <h4 style="margin-bottom: 5px;">{item['title']}</h4>
            <p style="color: #666; font-size: 0.8em; margin: 0;">
                {item['source']} • {item['published_at']}
            </p>
            <a href="{item['url']}" target="_blank" style="font-size: 0.9em;">Read more</a>
        </div>
        """
    return news_html

def main():
    st.set_page_config(
        page_title="🌍 Global Disaster Monitor",
        page_icon="🌍",
        layout="wide"
    )
    
    # Custom CSS for styling
    st.markdown("""
    <style>
        /* Main header styling */
        .header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            padding: 2rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Metric cards styling */
        .metric-card {
            background: white;
            border-radius: 0.5rem;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-left: 4px solid #6a11cb;
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background: #f8f9fa;
        }
        
        /* Section headers */
        .section-header {
            color: #6a11cb;
            border-bottom: 2px solid #6a11cb;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }
        
        /* Button styling */
        .stButton>button {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            border: none;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, #5a0db5 0%, #1a65e5 100%);
            color: white;
        }
        
        /* Input fields */
        .stTextInput>div>div>input {
            border-radius: 0.5rem;
            border: 1px solid #ddd;
            padding: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Enhanced Header with purple gradient
    st.markdown("""
    <div class="header">
        <h1 style="color: white; margin-bottom: 0.5rem;">🌍 Global Disaster Monitor</h1>
        <h3 style="color: white; opacity: 0.9; margin-top: 0;">Google Cloud × MongoDB Hackathon Project</h3>
        <p style="color: white; opacity: 0.8;">Real-time disaster tracking using GDELT data with AI analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize data handler
    global data_handler
    data_handler = DataHandler()
    
    # Load data
    with st.spinner("🔄 Loading disaster data from MongoDB..."):
        df = data_handler.load_disaster_data()
    
    if df.empty:
        st.error("❌ No data available. Please run the data collection script first.")
        return
    
    # Sidebar filters with improved styling
    st.sidebar.markdown("""
    <div style="background: #f0f0f0; padding: 1rem; border-radius: 0.5rem;">
        <h2 style="color: #6a11cb; margin-top: 0;">🔍 Advanced Filters</h2>
    """, unsafe_allow_html=True)
    
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
    top_countries = data_handler.get_top_countries(df)
    countries = sorted(df['country'].unique().tolist())
    selected_countries = st.sidebar.multiselect(
        "🏳️ Select Countries",
        countries,
        default=top_countries
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
    
    # Map view option
    st.sidebar.markdown("### 🗺️ Map View Options")
    use_clusters = st.sidebar.checkbox("Use Cluster Map", value=Config.CLUSTER_MAP_OPTION)
    
    # Live News Feed
    st.sidebar.markdown("""
    <div style="background: #f0f0f0; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;">
        <h2 style="color: #6a11cb; margin-top: 0;">📰 Live News Feed</h2>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("🔄 Refresh News"):
        st.cache_data.clear()
    
    news_items = data_handler.fetch_news(query=" OR ".join(selected_types)) if selected_types else []
    st.sidebar.markdown(create_news_feed(news_items), unsafe_allow_html=True)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    # Apply all filters
    df_filtered = df_country_filtered[
        (df_country_filtered['disaster_type'].isin(selected_types)) &
        (df_country_filtered['severity'] >= severity_range[0]) &
        (df_country_filtered['severity'] <= severity_range[1])
    ]
    
    # Main metrics with card styling
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
        <div class="metric-card">
            <h3 style="margin-top: 0; color: #6a11cb;">🌍 Total Disasters</h3>
            <p style="font-size: 2rem; font-weight: bold; margin-bottom: 0;">{}</p>
        </div>
        <div class="metric-card">
            <h3 style="margin-top: 0; color: #6a11cb;">📊 Avg Severity</h3>
            <p style="font-size: 2rem; font-weight: bold; margin-bottom: 0;">{:.1f}/5</p>
        </div>
        <div class="metric-card">
            <h3 style="margin-top: 0; color: #6a11cb;">📰 Total Mentions</h3>
            <p style="font-size: 2rem; font-weight: bold; margin-bottom: 0;">{:,}</p>
        </div>
        <div class="metric-card">
            <h3 style="margin-top: 0; color: #6a11cb;">🏳️ Countries Affected</h3>
            <p style="font-size: 2rem; font-weight: bold; margin-bottom: 0;">{}</p>
        </div>
    </div>
    """.format(
        len(df_filtered),
        df_filtered['severity'].mean() if not df_filtered.empty else 0,
        df_filtered['mentions'].sum() if not df_filtered.empty else 0,
        df_filtered['country'].nunique() if not df_filtered.empty else 0
    ), unsafe_allow_html=True)
    
    # Map section with improved header
    st.markdown("""
    <h2 class="section-header">🗺️ Interactive Disaster Map</h2>
    """, unsafe_allow_html=True)
    
    if not df_filtered.empty:
        if use_clusters and Config.CLUSTER_MAP_OPTION:
            cluster_fig = create_cluster_map(df_filtered)
            st.plotly_chart(cluster_fig, use_container_width=True)
        else:
            google_map_html = create_google_map_html(df_filtered)
            st.components.v1.html(google_map_html, height=520)
        st.info(f"📍 Showing {len(df_filtered)} disasters on map")
    else:
        st.warning("⚠️ No disasters match your current filters")
    
    # Analytics charts with improved header
    st.markdown("""
    <h2 class="section-header">📊 Disaster Analytics</h2>
    """, unsafe_allow_html=True)
    
    if not df_filtered.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            type_counts = df_filtered['disaster_type'].value_counts()
            fig_pie = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="🔥 Disaster Types Distribution",
                color=type_counts.index,
                color_discrete_map=Config.DISASTER_COLORS
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            severity_by_country = df_filtered.groupby('country')['severity'].mean().sort_values(ascending=False).head(10)
            fig_bar = px.bar(
                x=severity_by_country.values,
                y=severity_by_country.index,
                orientation='h',
                title="⚠️ Average Severity by Country",
                color=severity_by_country.values,
                color_continuous_scale='reds'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Correlation matrix
        st.plotly_chart(create_correlation_matrix(df_filtered), use_container_width=True)
    
    # Story Mode with improved header
    st.markdown("""
    <h2 class="section-header">📖 Quick Analysis: Recent Major Events</h2>
    """, unsafe_allow_html=True)
    
    df_stories = data_handler.get_top_stories(df_filtered)
    st.components.v1.html(create_story_mode(df_stories), height=400)
    
    # Report generation with improved styling
    st.markdown("""
    <h2 class="section-header">📝 Generate Report</h2>
    """, unsafe_allow_html=True)
    
    report_name = st.text_input("Enter report name", "Disaster_Report")
    if st.button("📄 Generate PDF Report"):
        with st.spinner("Generating report..."):
            report_bytes = generate_report(df_filtered, report_name, df_stories)
            st.download_button(
                label="⬇️ Download Report",
                data=report_bytes,
                file_name=f"{report_name}.pdf",
                mime="application/pdf"
            )
    
    # Footer with improved styling
    st.markdown("""
    <div style="margin-top: 4rem; padding: 1rem; text-align: center; color: #666; border-top: 1px solid #eee;">
        <p><strong>🚀 Powered by:</strong> Google Maps API • MongoDB Atlas • AI Topic Modeling • GDELT Project</p>
        <p style="font-size: 0.8rem;">© 2023 Global Disaster Monitor</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()