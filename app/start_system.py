import subprocess
import time
import sys

print("🚀 Starting Bronze pipeline...")

bronze = subprocess.Popen(
    [sys.executable, "pipelines/bronze/bronze_job.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# --- Czekamy aż Spark faktycznie wystartuje ---
spark_ready = False

while not spark_ready:
    line = bronze.stdout.readline()
    if line:
        print(line, end="")
        if "SparkSession" in line or "Started Spark" in line or "Spark context available" in line:
            spark_ready = True

    time.sleep(0.2)

print("\n✅ Spark is ready — starting UI...\n")

subprocess.Popen(
    ["streamlit", "run", "ui/app.py"]
)

# Podtrzymujemy wrapper
bronze.wait()
