# 🌍 Global Disaster Monitor

An interactive **2D** map-based dashboard built with **Streamlit** to monitor, analyze, and visualize global disasters using the **GDELT dataset**, **MongoDB Atlas**, and **Google Maps API**.

---

## 🔍 What It Does

- Fetches global disaster events from **GDELT**, filters & cleans them.
- Stores records in **MongoDB Atlas**, including coordinates (`lon`, `lat`), category, severity, sentiment, and NLP embeddings.
- Visualizes events on a **2D Google Map**, with country code and severity
- Supports semantic "vector search" to find **similar events** globally.
- Allows toggling between **clustered vs. normal markers**.
- Generates **correlation matrices** between countries based on disaster frequency/types.
- Enables **PDF/CSV report generation** for selected regions.


---

## 🔧 Built With

- **Streamlit** – Frontend dashboard 
- **Python** – Data pipeline + logic  
- **MongoDB Atlas** – Cloud storage with geospatial & **Vector Search**  
- **GDELT** – Real-time disaster events source  
- **Google Maps API** – Interactive 2D map overlays  
- **scikit-learn / UMAP** – Topic modeling, clustering & correlation analysis  
- **PyPDF2 / pandas** – Report generation  
- **pymongo** – MongoDB connector

---
<img width="1994" alt="Screenshot 2025-06-11 at 5 23 45 PM" src="https://github.com/user-attachments/assets/8da077d6-72f7-4747-8922-53bcb65def0c" />
<img width="1994" alt="Screenshot 2025-06-11 at 5 24 19 PM" src="https://github.com/user-attachments/assets/cb3ab8aa-12bc-47e5-ae6f-1ea64ca30af9" />

<img width="1994" alt="Screenshot 2025-06-11 at 5 24 09 PM" src="https://github.com/user-attachments/assets/6f2a17ca-de89-4a96-b880-4b866b8d728f" />
<img width="1994" alt="Screenshot 2025-06-11 at 5 24 39 PM" src="https://github.com/user-attachments/assets/1339c506-72a7-4c45-954d-65ac03555cb2" />


## 🚀 Project Setup


git clone https://github.com/Tanisha2212/Global-Disaster-Monitor.git
cd Global-Disaster-Monitor

## Update .env

MONGODB_URI=your_mongodb_atlas_uri

GOOGLE_MAPS_API_KEY=your_google_maps_key

