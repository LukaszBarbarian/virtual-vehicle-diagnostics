# 🚗 Vehicle Simulation & Streaming Pipeline

A modular vehicle simulation system with real-time streaming, data lake ingestion, and analytics-ready architecture.  
Designed as a **portfolio-grade Data Engineering project** with clear separation of concerns and production-like patterns.

---

## 🧠 Project Overview

This project simulates a vehicle in real time (engine, gearbox, thermals, wear, driver input) and streams telemetry events through Kafka into a Spark-based data pipeline.

The architecture follows a **Bronze–Silver–Gold** data lake pattern and is intentionally built to resemble real-world data engineering systems.

---

## 🏗️ High-Level Architecture

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


> Spark runs as a **separate process** and consumes events asynchronously from Kafka.  
> The simulation is fully decoupled from analytics and storage.

---

## 🧩 Key Components

### 🎮 Simulation & UI
- **Streamlit dashboard**
- Real-time gauges (RPM, speed, temperature, fuel)
- Throttle control
- Start / Stop engine lifecycle

### ⚙️ Simulation Core
- Engine, gearbox, vehicle physics
- Driver behavior
- Environment & wear models
- Deterministic simulation loop

### 📡 Event Streaming (Kafka)
- Simulation emits domain events (`simulation.raw`)
- Driver commands are consumed asynchronously
- Kafka acts as the **system boundary**

### 🔥 Spark Streaming
- Reads events from Kafka
- Writes raw, immutable events to Bronze layer
- Uses **Structured Streaming**
- Checkpointed & restart-safe

### 🗄️ Data Lake (Azure ADLS Gen2)
- **Bronze layer** stores raw JSON events
- Append-only, replayable
- Analytics-ready foundation

---

## 🥉 Bronze Layer (Current Stage)

**What is stored:**
- Raw Kafka events
- Full JSON payloads
- Kafka metadata (offset, partition, timestamp)

**Why:**
- Source of truth
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
