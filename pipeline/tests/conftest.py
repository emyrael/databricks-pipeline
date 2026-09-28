"""Shared Spark fixtures for local pipeline tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from databricks_pipeline.config import PipelineConfig


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """Local Spark session (no Databricks workspace required)."""
    # Keep driver and workers on the same interpreter (venv vs system mismatch).
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    session = (
        SparkSession.builder.master("local[2]")
        .appName("databricks-pipeline-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def local_config(tmp_path: Path) -> PipelineConfig:
    """Config pointing at a temp flat data dir for offline tests."""
    return PipelineConfig(
        catalog="test_catalog",
        bronze_schema="bronze",
        silver_schema="silver",
        gold_schema="gold",
        data_dir=tmp_path / "data",
        load_date=None,
    )
