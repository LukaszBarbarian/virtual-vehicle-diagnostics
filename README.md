# 🚗 Vehicle Simulation & Streaming Pipeline

A modular vehicle simulation system with real-time streaming, data lake ingestion, and analytics-ready architecture.  
Designed as a **portfolio-grade Data Engineering project** with clear separation of concerns and production-like patterns.

---

## 🧠 Project Overview

This project simulates a vehicle in real time (engine, gearbox, thermals, wear, driver input) and streams telemetry events through Kafka into a Spark-based data pipeline.

The architecture follows a **Bronze–Silver–Gold** data lake pattern and is intentionally built to resemble real-world data engineering systems.

---

## 🏗️ High-Level Architecture

```
[ Streamlit UI ]
        ↓
[ Simulation Runtime ]
        ↓
[ Kafka (Event Bus) ]
        ↓
[ Spark Structured Streaming ]
        ↓
[ Azure Data Lake Gen2 ]
        ↓
[ Bronze Layer (raw events) ]
```

Spark runs as a **separate process** and consumes events asynchronously from Kafka.  
The simulation is fully decoupled from analytics and storage.

---

## 🧩 Key Components

### 🎮 Simulation & UI
- Streamlit dashboard
- Real-time gauges (RPM, speed, temperature, fuel)
- Throttle control
- Start / Stop engine lifecycle

### ⚙️ Simulation Core
- Engine, gearbox, vehicle physics
- Driver behavior model
- Environment & wear models
- Deterministic simulation loop

### 📡 Event Streaming (Kafka)
- Simulation emits domain events (`simulation.raw`)
- Driver commands are consumed asynchronously
- Kafka acts as the system boundary

### 🔥 Spark Streaming
- Reads events from Kafka
- Writes raw, immutable events to the Bronze layer
- Uses Structured Streaming
- Checkpointed and restart-safe

### 🗄️ Data Lake (Azure ADLS Gen2)
- Bronze layer stores raw JSON events
- Append-only and replayable
- Analytics-ready foundation

---

## 🥉 Bronze Layer (Current Stage)

What is stored:
- Raw Kafka events
- Full JSON payloads
- Kafka metadata (offset, partition, timestamp)

Why:
- Single source of truth
- Full replay capability
- Decoupling of ingestion from downstream logic

Example Bronze record:

```json
{
  "kafka_ts": "2026-01-09T09:59:08",
  "partition": 0,
  "offset": 2934,
  "raw_event": "{ \"event_type\": \"simulation.raw\", ... }"
}
```

---

## ▶️ How to Run (Local Development)

### Prerequisites
```
- Python 3.10+
- Apache Kafka
- Apache Spark
- Azure Data Lake Storage Gen2
```

---

### 1️⃣ Start Kafka

```
zookeeper-server-start.sh config/zookeeper.properties
kafka-server-start.sh config/server.properties
```

Kafka broker:
```
localhost:9092
```

---

### 2️⃣ Start Spark Streaming (Bronze Ingestion)

```
python streaming/spark/stream_processor.py
```

Consumes Kafka events and writes raw data to the Bronze layer.

---

### 3️⃣ Start UI & Simulation

```
streamlit run ui/app.py
```

---

### 4️⃣ Use the Dashboard

```
- Click START ENGINE
- Increase throttle
- Observe real-time telemetry
- Events are streamed to Kafka and ingested into the Bronze layer
```

---

## 🚀 VS Code (Optional)

Use the compound launch configuration:

```
Run → START SYSTEM (UI + Spark)
```

This starts:
- Spark Streaming job
- Streamlit UI

as two independent processes.

---

## 🧱 Design Principles

- Clear separation of concerns
- Event-driven architecture
- Infrastructure decoupled from domain logic
- Restart-safe and replayable pipelines
- Production-inspired data lake design

---

## 🛣️ Roadmap

### 🥈 Silver Layer (Next)
- Batch processing from Bronze
- JSON parsing and schema validation
- Flattened, normalized Delta tables
- Data quality and completeness checks

### 🥇 Gold Layer
- Window aggregations
- Feature engineering
- ML-ready datasets

### 🤖 ML & Analytics
- MLflow integration
- Predictive models (wear, fuel usage, failures)
- Advanced analytics

---

## 📌 Tech Stack

- Python
- Streamlit
- Apache Kafka
- Apache Spark (Structured Streaming)
- Azure Data Lake Storage Gen2
- Delta Lake (planned)

---

## 🎯 Project Goal

This project demonstrates:
- Practical data engineering skills
- Streaming and batch processing patterns
- Clean architecture and system boundaries
- Azure and Spark integration
- Real-world trade-offs and design decisions

---

## 👋 Author

Built as a personal portfolio project with focus on correctness, clarity, and real-world applicability.
