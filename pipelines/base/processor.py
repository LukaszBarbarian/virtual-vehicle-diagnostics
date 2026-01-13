from abc import abstractmethod
from pyspark.sql import SparkSession


class BaseProcessor:
    def __init__(self, spark: SparkSession):
        self.spark = spark

    @abstractmethod    
    def read(self):
        raise NotImplementedError

    @abstractmethod
    def transform(self, df):
        return df
    
    @abstractmethod
    def process(self, df):
        return df

    @abstractmethod
    def write(self, df):
        raise NotImplementedError

    def run(self):
        df = self.read()                
        df = self.transform(df)
        df = self.process(df)
        self.write(df)
