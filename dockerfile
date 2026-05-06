ARG AIRFLOW_VERSION=2.9.2
ARG PYTHON_VERSION=3.10

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

ENV AIRFLOW_HOME=/opt/airflow

# Copy requirements
COPY requirements.txt /

# Install requirements  
RUN pip install --no-cache-dir -r /requirements.txt

# Copy etl_core business logic package
COPY etl_core /opt/airflow/etl_core

# Add etl_core to Python path so it's importable
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"