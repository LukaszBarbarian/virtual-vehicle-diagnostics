from abc import ABC, abstractmethod
from pyspark.sql import SparkSession, DataFrame

class BaseProcessor(ABC):
    """
    Abstract base class defining a standardized Spark processing pipeline.
    Follows the Template Method pattern to enforce a consistent ETL structure.
    """
    def __init__(self, spark: SparkSession):
        """
        Initializes the processor with an active Spark session.
        """
        self.spark = spark

    @abstractmethod    
    def read(self) -> DataFrame:
        """
        Extracts data from the source. Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """
        Applies initial data cleaning or schema adjustments.
        """
        return df
    
    @abstractmethod
    def process(self, df: DataFrame) -> DataFrame:
        """
        Executes core business logic and complex transformations.
        """
        return df

    @abstractmethod
    def write(self, df: DataFrame):
        """
        Loads the processed data into the target destination. Must be implemented by subclasses.
        """
        raise NotImplementedError

    def run(self):
        """
        Orchestrates the full execution flow: Read -> Transform -> Process -> Write.
        """
        df = self.read()                
        df = self.transform(df)
        df = self.process(df)
        return self.write(df)