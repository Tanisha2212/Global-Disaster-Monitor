import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    MONGO_URI = os.getenv('MONGO_URI')
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    
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
    
    DEFAULT_COUNTRIES_LIMIT = 5