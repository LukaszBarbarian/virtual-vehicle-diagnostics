## 🏎️ Simulator & Model Logic

### 🕹️ Vehicle Simulator (Physics-Based)
The simulator, built with **PySide6**, does more than just emit data; it mimics a real-world driving environment:
* **Physics Engine**: Calculates real-time relationships between RPM, Torque, Gear Ratios, and Speed.
* **Thermal Dynamics**: Simulates engine and brake temperature fluctuations based on load and environmental factors.
* **Driver Profiles**: Supports multiple profiles (e.g., Aggressive, Eco, Safe) that change how the vehicle is handled.
* **Event-Driven**: Emits high-frequency telemetry (approx. 10-50Hz) to Kafka, ensuring a realistic stream of "noisy" real-world data.

<img width="1154" height="824" alt="image" src="https://github.com/user-attachments/assets/eb6549da-e544-4fd4-a4d9-fb2158933b54" />


---

## 🧠 Project Overview

This project simulates vehicle physics and driver behavior in real-time, streaming high-frequency telemetry data through **Kafka** into a **Spark-powered Data Lake**. 

Unlike simple ingestion scripts, this repository implements a full **end-to-end lifecycle**:
1. **Simulation**: Real-time telemetry (PySide6 UI).
2. **Ingestion**: Structured Streaming into Bronze (Raw).
3. **Processing**: Automated transformation through Silver (Cleaned) and Gold (Aggregated) layers.
4. **Machine Learning**: Automated dataset preparation and model training.



---

## 🏗️ System Architecture

### 📡 Data Flow
* **Simulation (Producer)**: High-fidelity vehicle model emitting events to Kafka.
* **Spark Ingestion**: Consumes Kafka topics and writes to **Azure Data Lake Gen2** (Bronze).
* **Medallion Pipeline**: Orchestrated Spark jobs that promote data from Raw ➡️ Normalized ➡️ Feature sets.
* **ML Pipeline**: Consumes Gold data to generate train/test splits and train predictive models.

### 🧩 Core Components
* **`VehicleSimulator`**: Core logic for generating physics-based telemetry.
* **`KafkaStreamer`**: Handles asynchronous data transmission to Kafka topics.
* **`SilverProcessor`**: Method `process_raw_to_silver()` performs schema validation, timestamp normalization, and data cleaning.
* **`GoldProcessor`**: Method `aggregate_telemetry()` calculates rolling averages (RPM, Temp) and creates feature buckets.
* **`MLTrainingProcessor`**: Method `read()` loads Parquet datasets, while `process()` executes the training logic using Scikit-Learn and MLflow.

---

## 🤖 Machine Learning Insights

The pipeline includes an automated training module designed to classify driving styles based on high-frequency telemetry.

* **Model**: `RandomForestClassifier` (Scikit-Learn).
* **Configuration**: 300 estimators, max depth of 12, and `class_weight='balanced'` to handle minority class distributions without manual weight tuning.
* **Experiment Tracking**: Fully integrated with **MLflow**. Every run logs:
    * Accuracy metrics.
    * Model artifacts (serialized `.pkl`).
    * Feature importance (analyzing factors like `power_factor` and thermal trends).

<img width="1812" height="455" alt="image" src="https://github.com/user-attachments/assets/1f265cda-ffa3-4f7e-a6da-e57bb9a1007c" />

 

      
* **Data Handling**: Automated conversion from Spark DataFrames to Pandas for optimized local training after Gold-layer aggregation.
---

## ⚡ Real-Time Inference Engine

The project features a live AI inference system (`AIInferenceEngine`) that evaluates driving behavior every second using a sliding window approach.

### 🧠 How the AI "Thinks"
Unlike simple rule-based systems, our engine uses a **10-second rolling window** (300 samples at 30Hz) to understand context.
* **Sliding Window Buffer**: A `deque` collection stores the last 10 seconds of telemetry, allowing the model to analyze trends rather than just momentary spikes.
* **Feature Extraction**: On every prediction tick, the engine calculates:
    * **`rpm_std_10s`**: High variability in RPM often indicates aggressive downshifting or erratic acceleration.
    * **`power_factor`**: A derived metric (RPM × Load) representing the instantaneous stress on the powertrain.
    * **`throttle_avg_10s`**: Distinguishes between a quick overtake and sustained aggressive throttle usage.

### 🚦 Driving Style Classification
The engine compares the current driving pattern against the trained **Random Forest** model to output:
* **`NORMAL`**: Stable RPMs, moderate load, and smooth gear transitions.
* **`AGGRESSIVE`**: Triggered when the probability of aggressive behavior (e.g., high `load_max_10s` and erratic `rpm_range`) exceeds 50%.
* **Confidence Score**: The system provides a percentage-based score (e.g., "85% Aggressive") to indicate the model's certainty.



---

## 🧩 Core Components Deep Dive

* **`AIInferenceEngine`**: 
    * **`add_sample()`**: Feeds real-time data from the PySide6 UI into the buffer.
    * **`get_prediction()`**: Triggers the feature engineering and MLflow model scoring.
* **`MLflow Integration`**: Models are loaded directly via `mlflow.sklearn.load_model(model_uri)`, allowing the UI to always use the "latest" or a specifically tagged "production" model version.

---

## 🥉 Medallion Layers (Current Status)

| Layer | Purpose | Format |
| :--- | :--- | :--- |
| **Bronze** | Raw Kafka events (Immutable) | Parquet / JSON |
| **Silver** | Cleaned, validated, and flattened telemetry | Delta / Parquet |
| **Gold** | Feature-engineered datasets (RPM bins, thermal trends) | Delta / Parquet |
| **ML** | Train/Test splits and model metrics | Binary / Dataframes |

---

## ▶️ How to Run

### 0️⃣ Prerequisites
* Python 3.12+
* Apache Kafka (running locally at `localhost:9092`)
* Spark 3.x installed with Azure/Hadoop JARS
* Active Azure Storage Account

### 1️⃣ Simulation & UI
Start the vehicle cockpit to begin streaming telemetry:

```bash
python ui2/main_window.py
```

### 2️⃣ Run Data Pipelines (Silver → Gold)
To process raw data into analytics-ready tables:

```bash
# This triggers SilverProcessor and GoldProcessor sequentially
python pipelines/run_pipelines.py
```

### 3️⃣ Run ML Pipeline
To prepare datasets and train models:

```bash
# This triggers MLDatasetProcessor, MLSplitProcessor, and MLTrainingProcessor
python ml/run_ml_training.py
```

---

## 🔒 Security & Configuration (Refactoring Note)

The project follows production-ready security patterns:
* **Credential Isolation**: Secrets are never hardcoded; they are managed via `python-dotenv`.
* **Dynamic Configuration**: The `AppConfig` class builds `abfss` storage paths dynamically based on environment variables.
* **Refactoring Path**: Designed for easy migration to **Azure Key Vault**.

---

## 🧱 Design Principles
* **Separation of Concerns**: Simulation logic is entirely decoupled from the data engineering stack.
* **Idempotency**: Processing jobs can be re-run without duplicating data in the Lake.
* **Production-like Setup**: Uses `abfss` protocol and Spark Session Factories instead of local file system mocks.

---

## 📌 Tech Stack
* **Languages**: Python
* **ML Library**: Scikit-Learn & MLflow
* **GUI**: PySide6 (Qt)
* **Streaming**: Apache Kafka
* **Processing**: Apache Spark (Structured Streaming & Batch)
* **Cloud**: Azure Data Lake Gen2
* **Data Format**: Parquet / Delta Lake

---

## 🚀 Future Roadmap: Great Expectations
To ensure high data quality, the next step is integrating **Great Expectations**.

### What is Great Expectations?
It is a leading tool for **Data Quality (DQ)**. Instead of just checking if a pipeline "runs", it validates if the data itself is correct:
* **Unit tests for data**: Defines "Expectations" (e.g., *RPM value must be between 0 and 8000*).
* **Automated Documentation**: Generates clean reports (Data Docs) showing which data passed or failed.
* **Silver Layer Guard**: It will act as a gatekeeper between Bronze and Silver to prevent "garbage" data from polluting the Lake.


👋 **Author**
Built as a professional portfolio project focusing on high-load data engineering patterns, clean architecture, and ML integration.


