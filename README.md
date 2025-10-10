# Project ARES: Automated Road Network Change Detection System

## 🚀 Overview

**Project ARES** (Automated Road Extraction System) is a Final Year Project designed to **automate the monitoring and updating of road network infrastructure** using satellite imagery and geospatial analysis.

It is a full-stack application built with a **React (Vite) frontend**, a **Python (Flask) backend**, and a **PostgreSQL/PostGIS** database, integrating a deep learning model for road segmentation.

### Key Features

- **Automated Road Segmentation:** Utilizes a custom U-Net based model (download link below) to extract road features (MultiLineString GeoJSON) from high-resolution TIFF satellite images.
- **Geospatial Change Detection:** Implements PostGIS topological operations to efficiently calculate **Additions (New Roads)** and **Deletions (Removed Roads)** between two temporal snapshots.
- **Area of Interest (AOI) Management:** Allows users to define, track, and schedule automated road change monitoring for specific geographic regions.
- **Full-Stack MVP:** Includes user authentication, database persistence, and a map-based UI for visualization.

---

## 🛠️ Technology Stack

| Component    | Technology                                            | Description                                                                                 |
| :----------- | :---------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| **Frontend** | React, Vite, Tailwind CSS, Leaflet                    | Interactive dashboard for map visualization and AOI management.                             |
| **Backend**  | Python, Flask, Flask-Bcrypt, CORS                     | REST API for authentication, AOI CRUD, and orchestration of the ML pipeline.                |
| **Database** | PostgreSQL, **PostGIS**                               | Geospatial data storage (for `road_features` and `aois.bbox`) and fast topological queries. |
| **ML/Geo**   | PyTorch/TensorFlow (via Kaggle), GDAL/Rasterio, Fiona | Custom scripts for road segmentation and GeoJSON processing.                                |

---

## 📸 Project Screenshots

| Dashboard View | Change Detection Result | AOI Management List | Initial Road Extraction |
| :------------: | :---------------------: | :-----------------: | :---------------------: |
|                |                         |                     |                         |

---

## ⚙️ Setup and Installation

### 1\. Model & Data Setup

The model used for road segmentation is hosted on Hugging Face, and the training notebook is on Kaggle.

1.  **Download the Model:**
    - **Hugging Face Space:** [Hugging Face Space Link Here]
    - Download the model weights file (e.g., `unet_road_segmentation_weights.pth` or `.h5`) and place it inside the **`backend/scripts/`** folder.

2.  **Create Test Images:**
    - The backend expects test image files (`.tiff` format) in the root of the **`backend/`** directory for initial AOI creation.
    - Please download at least four unique satellite TIFF images (e.g., from **OpenAerialMap** or a similar source) and name them:
      - `test_image_1.tiff`
      - `test_image_2.tiff`
      - `test_image_3.tiff`
      - `test_image_4.tiff`

### 2\. Database Setup (PostgreSQL with PostGIS)

This step requires you to have **PostgreSQL** installed locally.

1.  **Install PostGIS Extension:**
    - Connect to your PostgreSQL server and create the database and the PostGIS extension using the credentials from `config.py` (e.g., user `akash`, database `ares_mvp`).

    <!-- end list -->

    ```bash
    # 1. Log into your postgres shell
    psql -U postgres

    # 2. Create the database (if it doesn't exist)
    CREATE DATABASE ares_mvp;

    # 3. Connect to the new database
    \c ares_mvp;

    # 4. Enable the PostGIS extension (Crucial for geometry types)
    CREATE EXTENSION postgis;

    # 5. Exit psql
    \q
    ```

2.  **Create Schema Tables:**
    - The schema SQL is in `backend/utils/db_setup.py`. Run the script to initialize the tables.

    <!-- end list -->

    ```bash
    # From the project root directory
    python backend/utils/db_setup.py
    ```

### 3\. Backend Environment

1.  **Configuration:** Ensure your `backend/config.py` matches your database setup.

    ```python
    # backend/config.py
    DB_HOST = "localhost"
    DB_NAME = "ares_mvp"
    DB_USER = "akash" # Ensure this user exists in your Postgres
    DB_PASSWORD = "akash"
    DB_PORT = 5432
    ```

2.  **ML/Geo Environment:**
    - The road segmentation model is run by the backend and requires specialized libraries like **GDAL, Fiona, Rasterio, and PyTorch/TensorFlow** which can be challenging to set up.
    - You can set up a **Conda/venv** environment based on the `requirements.txt` file located in the `backend` folder.

    <!-- end list -->

    ```bash
    # From the project root directory
    cd backend
    python3 -m venv venv
    source venv/bin/activate # On Windows, use: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Run the Backend API:**

    ```bash
    # From the backend directory
    export FLASK_APP=app.py
    flask run

    # The API will run at http://127.0.0.1:5000/
    ```

### 4\. Frontend Environment

1.  **Install Dependencies:**

    ```bash
    # From the project root directory
    cd frontend # Assuming your frontend is in a 'frontend' folder
    npm install
    ```

2.  **Run the Frontend:**

    ```bash
    npm run dev

    # The application will run at http://localhost:5173/
    ```

---

## 🧠 Model & Training Resources

The road segmentation model is based on the **U-Net** architecture, trained on satellite imagery to classify pixels as either "road" or "non-road." The PostGIS process then vectorizes these pixel outputs into structured line geometries.

| Resource              | Link                           | Description                                                                                       |
| :-------------------- | :----------------------------- | :------------------------------------------------------------------------------------------------ |
| **Training Notebook** | [Kaggle Notebook Link Here]    | Detailed steps, data augmentation, and code used to train the final road extraction model.        |
| **Model Download**    | [Hugging Face Space Link Here] | Direct link to the model weights (`.pth` or `.h5` file) used in the `scripts/model_processor.py`. |
