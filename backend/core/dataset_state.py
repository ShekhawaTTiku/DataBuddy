"""Dataset State public interface; profiling implementation remains local."""
from backend.core.dataset_profiler import DatasetProfile, SUPPORTED_EXTENSIONS, load_and_profile

DatasetState = DatasetProfile

__all__ = ["DatasetState", "DatasetProfile", "SUPPORTED_EXTENSIONS", "load_and_profile"]
