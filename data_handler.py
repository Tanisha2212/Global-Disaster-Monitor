from pymongo import MongoClient
import pandas as pd
from datetime import datetime
from config import Config

class DataHandler:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, tls=True, tlsInsecure=True)
        self.db = self.client["gdelt"]
        self.collection = self.db["disasters"]
    
    def load_disaster_data(self):
        disasters = list(self.collection.find({}).limit(2000))
        
        df_data = []
        for doc in disasters:
            coords = doc['location']['coordinates']
            location_parts = str(doc.get('location_name', '')).split(', ')
            
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
    
    def get_top_countries(self, df, limit=Config.DEFAULT_COUNTRIES_LIMIT):
        return df['country'].value_counts().head(limit).index.tolist()