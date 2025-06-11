from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import requests
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
                'goldstein': doc.get('goldstein', 0),
                'tone': doc.get('tone', 0)
            })
        
        return pd.DataFrame(df_data)
    
    def get_top_countries(self, df, limit=Config.DEFAULT_COUNTRIES_LIMIT):
        return df['country'].value_counts().head(limit).index.tolist()
    
    def get_correlation_matrix(self, df):
        numeric_df = df[['severity', 'mentions', 'goldstein', 'tone']]
        return numeric_df.corr()
    
    def get_top_stories(self, df, limit=5):
        return df.sort_values(['severity', 'mentions'], ascending=False).head(limit)
    
    def fetch_news(self, query="disaster", limit=5):
        if not Config.NEWS_API_KEY:
            return []
            
        try:
            url = f"https://newsapi.org/v2/everything?q={query}&apiKey={Config.NEWS_API_KEY}&pageSize={limit}"
            response = requests.get(url)
            articles = response.json().get('articles', [])
            return [{
                'title': a.get('title', ''),
                'source': a.get('source', {}).get('name', ''),
                'url': a.get('url', ''),
                'published_at': a.get('publishedAt', '')[:10]
            } for a in articles]
        except:
            return []