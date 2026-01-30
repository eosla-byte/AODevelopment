FROM python:3.11-slim

# Install Java and system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk-headless \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set Environment Variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV LD_LIBRARY_PATH=$JAVA_HOME/lib/server
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /app

# Install Python Dependencies
# We need to copy requirements from root and service
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/services/bim/requirements.txt /app/backend/services/bim/requirements.txt

# Install root requirements
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install service requirements
RUN pip install --no-cache-dir -r backend/services/bim/requirements.txt

# Copy the specific service code
# We need to copy the relevant parts of the monorepo to maintain imports
# Copying 'backend' directory
COPY backend /app/backend

# Set PYTHONPATH to root so 'backend.common' imports work
ENV PYTHONPATH=/app

# Command to run the service
# We run from /app/backend/services/bim but need PYTHONPATH set
WORKDIR /app/backend/services/bim

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
