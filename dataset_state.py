"""Dataset State public interface; profiling implementation remains local."""
from dataset_profiler import DatasetProfile, load_and_profile

DatasetState = DatasetProfile

__all__ = ["DatasetState", "DatasetProfile", "load_and_profile"]
