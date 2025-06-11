# Global-Disaster-Monitor


---

## 🔍 Project Overview

An **interactive web dashboard** that visualizes global disasters using **real-time data from the GDELT Project**, enhanced by intelligent search and mapping features. This solution harnesses the power of **MongoDB Atlas** (with geospatial and vector search capabilities), **Streamlit**, and **Google Maps API** to offer data-driven insights into crises worldwide.

---

## ⚡ Core Features

- 🗺️ **Geospatial Dashboard**  
  Visualize disasters globally using **latitude and longitude** stored in MongoDB, rendered via Google Maps integration.

- 🔬 **MongoDB Atlas-powered Analysis**  
  - Store GDELT event records (hourly snapshots or bulk imports) in **Atlas collections**  
  - Query with **2dsphere geospatial indexing** (for location-based filtering)  
  - Use **Atlas Vector Search** to find semantically similar events based on text embeddings

- 📡 **Streamlit UI**  
  - Interactive components allow users to filter by country, state, district, date range, and disaster type  
  - Clickable map markers reveal event metadata (`event_type`, `severity`, `date`, `description`) and links to related news  
  - "Find similar events" powered by vector search

---

## 🛠️ Tech & Services Used

| Layer            | Tools & Services |
|------------------|------------------|
| **Backend DB**   | MongoDB Atlas (geospatial, vector search) |
| **Data Source**  | GDELT Global Events dataset |
| **API & Data Fetching** | Python scripts to load/clean and store data |
| **Search & Analytics** | Atlas Vector Search (semantic similarity), Aggregations |
| **Frontend**     | Streamlit |
| **Mapping**      | Google Maps JavaScript API |
| **Deployment**   | (Optional) Google Cloud Run |
| **Graphical Analysis** | Atlas Charts (optional)|

---

## 🚀 Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/Tanisha2212/Global-Disaster-Monitor.git
cd Global-Disaster-Monitor
