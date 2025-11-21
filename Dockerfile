FROM apache/airflow:2.10.2

USER root

# Install any system dependencies if needed
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     <package-name> \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements file
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /requirements.txt

