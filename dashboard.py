import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from data_handler import DataHandler
from config import Config
from report_generator import generate_report

def create_google_map_html(df_filtered):
    """Create Google Maps HTML with markers"""
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

def create_heatmap(df_filtered):
    """Create a density heatmap of disasters"""
    fig = px.density_mapbox(
        df_filtered,
        lat='lat',
        lon='lon',
        z='severity',
        radius=20,
        center=dict(lat=20, lon=0),
        zoom=1,
        mapbox_style="stamen-terrain",
        title="🌋 Disaster Severity Heatmap",
        color_continuous_scale="hot"
    )
    return fig

def create_disaster_network(df_filtered):
    """Create a network graph of actors involved in disasters"""
    if len(df_filtered) < 2:
        return None
    
    # Prepare nodes and links data
    actors = pd.concat([df_filtered['actor1'], df_filtered['actor2']]).value_counts().head(10)
    
    nodes = [{'name': actor, 'group': 1} for actor in actors.index]
    links = []
    
    for _, row in df_filtered.iterrows():
        if row['actor1'] and row['actor2'] and row['actor1'] in actors.index and row['actor2'] in actors.index:
            links.append({
                'source': row['actor1'],
                'target': row['actor2'],
                'value': row['severity']
            })
    
    if not links:
        return None
    
    # Create the network graph
    fig = go.Figure()
    
    # Add edges
    for link in links:
        fig.add_trace(go.Scatter(
            x=[link['source'], link['target']],
            y=[1, 1],
            mode='lines',
            line=dict(width=link['value']*0.5, color='#888'),
            hoverinfo='none'
        ))
    
    # Add nodes
    fig.add_trace(go.Scatter(
        x=[node['name'] for node in nodes],
        y=[1]*len(nodes),
        mode='markers',
        marker=dict(
            size=20,
            color=[Config.DISASTER_COLORS.get('armed_conflict', '#666666')]*len(nodes)
        ),
        text=[node['name'] for node in nodes],
        hoverinfo='text'
    ))
    
    fig.update_layout(
        title='🤝 Actor Network in Disasters',
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="🌍 Global Disaster Monitor - Google x MongoDB",
        page_icon="🌍",
        layout="wide"
    )
    
    # Header
    st.markdown("""
    # 🌍 Global Disaster Monitor
    ### Google Cloud × MongoDB Hackathon Project
    Real-time disaster tracking using GDELT data with AI analysis
    """)
    
    # Load data
    data_handler = DataHandler()
    with st.spinner("🔄 Loading disaster data from MongoDB..."):
        df = data_handler.load_disaster_data()
    
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
    
    # Country filter - show only top 5 initially
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
        # First row of charts
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
        
        # Second row of charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig_heatmap = create_heatmap(df_filtered)
            st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with col2:
            fig_network = create_disaster_network(df_filtered)
            if fig_network:
                st.plotly_chart(fig_network, use_container_width=True)
            else:
                st.info("Not enough data to show actor network")
        
        # Report generation
        st.markdown("## 📝 Generate Report")
        report_name = st.text_input("Enter report name", "Disaster_Report")
        if st.button("📄 Generate PDF Report"):
            report_bytes = generate_report(df_filtered, report_name)
            st.download_button(
                label="⬇️ Download Report",
                data=report_bytes,
                file_name=f"{report_name}.pdf",
                mime="application/pdf"
            )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **🚀 Powered by:** Google Maps API • MongoDB Atlas • AI Topic Modeling • GDELT Project
    """)

if __name__ == "__main__":
    main()