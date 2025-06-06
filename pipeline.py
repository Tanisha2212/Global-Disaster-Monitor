#pipeline.py
import pandas as pd
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
from datetime import datetime
import logging

# MongoDB connection
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Enhanced MongoDB Setup with SSL Fix ---
MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

client = MongoClient(MONGO_URI, tls=True, tlsInsecure=True)
db = client["gdelt"]
collection = db["disasters"]

def create_text_features():
    """Create text features from disaster data"""
    # Fetch data from MongoDB
    disasters = list(collection.find({}))
    
    # Create text for topic modeling
    texts = []
    for doc in disasters:
        text_parts = [
            str(doc.get('actor1', '')),
            str(doc.get('actor2', '')),
            str(doc.get('location_name', '')),
            str(doc.get('disaster_type', '')),
            ' '.join(doc.get('keywords', []))
        ]
        # Filter out empty strings and 'None' strings, then join
        clean_parts = [part for part in text_parts if part and part != 'None' and part.strip()]
        text = ' '.join(clean_parts).lower() if clean_parts else 'unknown disaster'
        texts.append(text)
    
    return disasters, texts

def apply_topic_modeling(texts, n_topics=8):
    """Apply LDA topic modeling"""
    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # LDA Topic Modeling
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=10
    )
    
    doc_topic_probs = lda.fit_transform(tfidf_matrix)
    
    # Get topic keywords
    feature_names = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(lda.components_):
        top_words = [feature_names[i] for i in topic.argsort()[-10:][::-1]]
        topics.append({
            'topic_id': topic_idx,
            'keywords': top_words,
            'name': f"Topic_{topic_idx}"
        })
    
    return doc_topic_probs, topics

def spatial_temporal_clustering(disasters):
    """Cluster events by location and time using DBSCAN"""
    # Prepare features: lat, lon, time (days since epoch)
    features = []
    for doc in disasters:
        try:
            coords = doc['location']['coordinates']
            date_days = (doc['date'] - datetime(1970, 1, 1)).days
            
            features.append([
                float(coords[1]),  # latitude
                float(coords[0]),  # longitude  
                date_days / 365.25,  # years since epoch (normalize time)
                float(doc.get('severity', 1))
            ])
        except (KeyError, TypeError, ValueError) as e:
            # Skip invalid records
            logging.warning(f"Skipping invalid record: {e}")
            continue
    
    if len(features) < 3:
        logging.warning("Not enough valid records for clustering")
        return [-1] * len(disasters)
    
    features = np.array(features)
    
    # Scale features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # DBSCAN clustering
    dbscan = DBSCAN(eps=0.3, min_samples=3)
    clusters = dbscan.fit_predict(features_scaled)
    
    # Pad clusters array to match disasters length
    full_clusters = [-1] * len(disasters)
    valid_idx = 0
    for i, doc in enumerate(disasters):
        try:
            coords = doc['location']['coordinates']
            if coords and len(coords) >= 2:
                full_clusters[i] = clusters[valid_idx]
                valid_idx += 1
        except (KeyError, TypeError):
            continue
    
    return full_clusters

def update_mongodb_with_analysis():
    """Update MongoDB documents with ML analysis results"""
    print("Starting ML analysis...")
    
    # Get data and create text features
    disasters, texts = create_text_features()
    print(f"Processing {len(disasters)} disasters...")
    
    if not disasters:
        print("No disasters found in database!")
        return 0, 0, 0
    
    # Topic modeling
    doc_topic_probs, topics = apply_topic_modeling(texts)
    print(f"Created {len(topics)} topics")
    
    # Spatial-temporal clustering
    clusters = spatial_temporal_clustering(disasters)
    unique_clusters = len(set(c for c in clusters if c != -1))
    print(f"Created {unique_clusters} spatial-temporal clusters")
    
    # Update each document
    updated_count = 0
    for i, doc in enumerate(disasters):
        try:
            # Get dominant topic
            dominant_topic = np.argmax(doc_topic_probs[i])
            topic_confidence = float(doc_topic_probs[i][dominant_topic])
            
            # Update document
            update_data = {
                'topic_id': int(dominant_topic),
                'topic_confidence': topic_confidence,
                'topic_keywords': topics[dominant_topic]['keywords'][:5],
                'cluster_id': int(clusters[i]) if clusters[i] != -1 else None,
                'analysis_date': datetime.now()
            }
            
            collection.update_one(
                {'_id': doc['_id']},
                {'$set': update_data}
            )
            updated_count += 1
            
        except Exception as e:
            logging.error(f"Error updating document {doc.get('_id')}: {e}")
            continue
    
    # Store topic metadata
    try:
        topics_collection = db["topics"]
        topics_collection.delete_many({})  # Clear existing
        topics_collection.insert_many(topics)
        print(f"Stored {len(topics)} topic definitions")
    except Exception as e:
        logging.error(f"Error storing topics: {e}")
    
    print(f"ML analysis completed! Updated {updated_count} documents")
    return len(disasters), len(topics), unique_clusters

if __name__ == "__main__":
    # Run the ML pipeline
    docs_processed, topics_created, clusters_created = update_mongodb_with_analysis()
    
    print(f"\n=== ML Pipeline Results ===")
    print(f"Documents processed: {docs_processed}")
    print(f"Topics created: {topics_created}")
    print(f"Clusters created: {clusters_created}")
    
    # Sample results
    sample = list(collection.find({}).limit(3))
    for doc in sample:
        print(f"\nSample: {doc['disaster_type']} in {doc['location_name']}")
        print(f"Topic: {doc.get('topic_keywords', [])}")
        print(f"Cluster: {doc.get('cluster_id', 'N/A')}")