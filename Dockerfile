# ==============================================================================
# Firmware Validation Framework - Container Image for Render & Cloud Deployment
# Combines compiled C11 controller (Project 1) and Python validation engine (Project 2)
# ==============================================================================

FROM python:3.12-slim

# Install system dependencies: GCC compiler and Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone and compile Project 1 (C11 Sensor Fault Controller)
WORKDIR /opt/sensor-fault-controller
RUN git clone https://github.com/Sargunan-1619/sensor-fault-controller.git . \
    && mkdir -p build \
    && gcc -std=c11 -Wall -Wextra src/*.c -Iinclude -o build/sensor_controller -lm \
    && chmod +x build/sensor_controller

# Set up Project 2 (Python Firmware Validation Framework)
WORKDIR /app
COPY . /app

# Ensure binary discovery points to the compiled Linux binary
ENV SENSOR_CONTROLLER_BIN=/opt/sensor-fault-controller/build/sensor_controller
ENV HOST=0.0.0.0
ENV PORT=8080

# Execute validation suite during build to generate initial baseline report
RUN python validate.py

# Expose HTTP port
EXPOSE 8080

# Launch dashboard server
CMD ["python", "server.py"]
