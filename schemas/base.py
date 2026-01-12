from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType,
    BooleanType, MapType
)

# payload.modules.engine.engine_rpm itd.
EngineSchema = StructType([
    StructField("engine_rpm", DoubleType()),
    StructField("engine_temp_c", DoubleType()),
    StructField("oil_temp_c", DoubleType()),
    StructField("fuel_rate_lph", DoubleType()),
])

VehicleSchema = StructType([
    StructField("speed_kmh", DoubleType()),
    StructField("acc_mps2", DoubleType()),
    StructField("load", DoubleType()),
])

WearSchema = StructType([
    StructField("engine_wear", DoubleType()),
    StructField("cooling_efficiency_loss", DoubleType()),
    StructField("torque_loss_factor", DoubleType()),
])

ModulesSchema = StructType([
    StructField("engine", EngineSchema),
    StructField("vehicle", VehicleSchema),
    StructField("wear", WearSchema),
])

PayloadSchema = StructType([
    StructField("time", DoubleType()),
    StructField("step", IntegerType()),
    StructField("modules", ModulesSchema),
])

BaseEventSchema = StructType([
    StructField("event_type", StringType()),
    StructField("event_version", IntegerType()),
    StructField("event_id", StringType()),
    StructField("timestamp", DoubleType()),
    StructField("payload", PayloadSchema),
])
