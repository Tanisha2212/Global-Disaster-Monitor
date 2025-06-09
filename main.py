#main.py
import pandas as pd
import requests
import zipfile
import io
from pymongo import MongoClient
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.cluster import KMeans
import re
import logging
import ssl

# --- Enhanced MongoDB Setup with SSL Fix ---
MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

# Connect to MongoDB
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsInsecure=True,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
        socketTimeoutMS=20000
    )
    
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    raise

db = client["gdelt"]
collection = db["disasters"]

# Create indexes for better performance
try:
    collection.create_index([("location", "2dsphere")])
    collection.create_index([("date", 1)])
    collection.create_index([("event_code", 1)])
    collection.create_index([("disaster_type", 1)])
    print("Indexes created successfully!")
except Exception as e:
    print(f"Index creation failed: {e}")

# --- Disaster Event Codes (GDELT specific) ---
DISASTER_CODES = {
    # Natural Disasters
    '0231': 'earthquake',
    '0232': 'flood', 
    '0233': 'drought',
    '0234': 'hurricane_typhoon',
    '0235': 'wildfire',
    '0236': 'volcanic_activity',
    '0237': 'landslide',
    '0238': 'tsunami',
    # Man-made Disasters
    '180': 'terrorist_attack',
    '190': 'armed_conflict',
    '200': 'explosion',
    '145': 'industrial_accident',
    '1283': 'chemical_spill',
    '1284': 'nuclear_incident'
}

def calculate_severity(goldstein, mentions, tone):
    """Calculate disaster severity on scale 1-5"""
    severity_score = 0
    
    # Goldstein scale contribution (more negative = more severe)
    if goldstein <= -8:
        severity_score += 3
    elif goldstein <= -5:
        severity_score += 2
    elif goldstein <= -2:
        severity_score += 1
    
    # Media attention (mentions)
    if mentions >= 100:
        severity_score += 2
    elif mentions >= 50:
        severity_score += 1
    
    # Tone (more negative = more severe)
    if tone <= -5:
        severity_score += 1
    
    return min(max(severity_score, 1), 5)

def extract_keywords_from_actors(actor1, actor2):
    """Extract disaster-related keywords from actor names"""
    disaster_keywords = [
        'earthquake', 'flood', 'fire', 'storm', 'hurricane', 'typhoon',
        'drought', 'tsunami', 'volcano', 'landslide', 'avalanche',
        'explosion', 'accident', 'spill', 'leak', 'collapse'
    ]
    
    text = f"{actor1} {actor2}".lower() if actor1 and actor2 else ""
    found_keywords = [kw for kw in disaster_keywords if kw in text]
    return found_keywords

def classify_disaster_type(event_code, base_code, keywords, actor1, actor2):
    """Classify disaster type based on codes and keywords"""
    if str(event_code) in DISASTER_CODES:
        return DISASTER_CODES[str(event_code)]
    
    if str(base_code) in DISASTER_CODES:
        return DISASTER_CODES[str(base_code)]
    
    # Keyword-based classification
    text = f"{actor1} {actor2}".lower() if actor1 and actor2 else ""
    
    if any(kw in text for kw in ['earthquake', 'quake']):
        return 'earthquake'
    elif any(kw in text for kw in ['flood', 'flooding']):
        return 'flood'
    elif any(kw in text for kw in ['fire', 'wildfire']):
        return 'wildfire'
    elif any(kw in text for kw in ['storm', 'hurricane', 'typhoon', 'cyclone']):
        return 'storm'
    elif any(kw in text for kw in ['explosion', 'blast']):
        return 'explosion'
    elif any(kw in text for kw in ['accident', 'crash']):
        return 'accident'
    else:
        return 'other'

def download_and_process_gdelt(date_str):
    """Download and process GDELT data for a specific date"""
    # FIX: Use the date_str parameter instead of hardcoded date
    url = f"http://data.gdeltproject.org/events/{date_str}.export.CSV.zip"
    
    # GDELT column names
    columns = [
        "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
        "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
        "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
        "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
        "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
        "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
        "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
        "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode",
        "QuadClass", "GoldsteinScale", "NumMentions", "NumSources",
        "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
        "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_Lat",
        "Actor1Geo_Long", "Actor1Geo_FeatureID", "Actor2Geo_Type",
        "Actor2Geo_FullName", "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code",
        "Actor2Geo_Lat", "Actor2Geo_Long", "Actor2Geo_FeatureID",
        "ActionGeo_Type", "ActionGeo_FullName", "ActionGeo_CountryCode",
        "ActionGeo_ADM1Code", "ActionGeo_Lat", "ActionGeo_Long",
        "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL"
    ]
    
    try:
        print(f"Downloading from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Extract and read CSV from zip
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = f"{date_str}.export.CSV"
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file, sep='\t', names=columns, dtype=str, na_values=[''])
        
        # Filter for disaster-related events
        disaster_df = df[
            (df['EventCode'].isin([str(code) for code in DISASTER_CODES.keys()])) |
            (df['EventBaseCode'].isin([str(code) for code in DISASTER_CODES.keys()])) |
            (df['Actor1Name'].str.contains('EARTHQUAKE|FLOOD|FIRE|STORM|HURRICANE|EXPLOSION', 
                                          case=False, na=False)) |
            (df['Actor2Name'].str.contains('EARTHQUAKE|FLOOD|FIRE|STORM|HURRICANE|EXPLOSION', 
                                          case=False, na=False))
        ].copy()
        
        print(f"Found {len(disaster_df)} disaster-related events for {date_str}")
        return disaster_df
        
    except requests.exceptions.RequestException as e:
        print(f"Network error downloading GDELT data for {date_str}: {e}")
        return None
    except zipfile.BadZipFile as e:
        print(f"Invalid zip file for {date_str}: {e}")
        return None
    except Exception as e:
        print(f"Error processing GDELT data for {date_str}: {e}")
        return None

def transform_to_documents(df):
    """Transform DataFrame to MongoDB documents"""
    docs = []
    
    for _, row in df.iterrows():
        try:
            # Extract location (prefer ActionGeo, fallback to Actor1Geo)
            lat = row.get('ActionGeo_Lat') or row.get('Actor1Geo_Lat')
            lon = row.get('ActionGeo_Long') or row.get('Actor1Geo_Long')
            
            if pd.isna(lat) or pd.isna(lon):
                continue
                
            lat, lon = float(lat), float(lon)
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                continue
            
            # Extract and clean data
            event_code = str(row.get('EventCode', ''))
            base_code = str(row.get('EventBaseCode', ''))
            goldstein = float(row.get('GoldsteinScale', 0))
            mentions = int(row.get('NumMentions', 0))
            tone = float(row.get('AvgTone', 0))
            
            # Classification and analysis
            keywords = extract_keywords_from_actors(
                row.get('Actor1Name'), row.get('Actor2Name'))
            disaster_type = classify_disaster_type(
                event_code, base_code, keywords,
                row.get('Actor1Name'), row.get('Actor2Name'))
            severity = calculate_severity(goldstein, mentions, tone)
            
            doc = {
                "event_id": str(row["GLOBALEVENTID"]),
                "date": datetime.strptime(str(row["SQLDATE"]), "%Y%m%d"),
                "actor1": row.get("Actor1Name"),
                "actor2": row.get("Actor2Name"),
                "event_code": event_code,
                "base_code": base_code,
                "root_code": str(row.get("EventRootCode", "")),
                "goldstein": goldstein,
                "tone": tone,
                "mentions": mentions,
                "articles": int(row.get("NumArticles", 0)),
                "sources": int(row.get("NumSources", 0)),
                "location": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "country_code": row.get("ActionGeo_CountryCode") or row.get("Actor1Geo_CountryCode"),
                "location_name": row.get("ActionGeo_FullName") or row.get("Actor1Geo_FullName"),
                "source_url": row.get("SOURCEURL"),
                "disaster_type": disaster_type,
                "severity": severity,
                "keywords": keywords,
                "processed_date": datetime.now()
            }
            docs.append(doc)
            
        except (ValueError, TypeError) as e:
            logging.warning(f"Error processing row {row.get('GLOBALEVENTID')}: {e}")
            continue
    
    return docs

def collect_disaster_data(start_date, end_date):
    """Collect disaster data for date range"""
    current_date = datetime.strptime(start_date, "%Y%m%d")
    end_date_obj = datetime.strptime(end_date, "%Y%m%d")
    
    total_docs = 0
    
    while current_date <= end_date_obj:
        date_str = current_date.strftime("%Y%m%d")
        print(f"Processing {date_str}...")
        
        df = download_and_process_gdelt(date_str)
        if df is not None and not df.empty:
            docs = transform_to_documents(df)
            if docs:
                try:
                    # Insert with duplicate handling
                    for doc in docs:
                        collection.replace_one(
                            {"event_id": doc["event_id"]},
                            doc,
                            upsert=True
                        )
                    total_docs += len(docs)
                    print(f"Processed {len(docs)} disaster records for {date_str}")
                except Exception as e:
                    logging.error(f"Error inserting data for {date_str}: {e}")
        else:
            print(f"No disaster data found for {date_str}")
        
        current_date += timedelta(days=1)
    
    print(f"Total disaster records collected: {total_docs}")
    return total_docs

# --- Run Data Collection ---
if __name__ == "__main__":
    # FIX: Use correct date range (2024, not 2025)
    # Collect data for May 26 - June 2, 2024
    start_date = "20250526"  # May 26, 2025
    end_date = "20250602"    # June 2, 2025
    
    print(f"Collecting GDELT disaster data from {start_date} to {end_date}")
    collect_disaster_data(start_date, end_date)
    
    # Verify collection
    total_count = collection.count_documents({})
    print(f"Total documents in collection: {total_count}")
    
    # Sample query by date range
    sample_disasters = list(collection.find({
        "date": {
            "$gte": datetime(2024, 5, 26),
            "$lte": datetime(2024, 6, 2)
        }
    }).limit(10))
    
    print(f"Sample disasters from date range: {len(sample_disasters)} found")
    for disaster in sample_disasters:
        print(f"- {disaster['date'].strftime('%Y-%m-%d')}: {disaster['disaster_type'].title()} in {disaster['location_name']} "
              f"(Severity: {disaster['severity']})")