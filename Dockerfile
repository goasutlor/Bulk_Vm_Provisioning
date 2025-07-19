# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . .

# Debug: List files
RUN ls -la

# Install dependencies and the package in development mode
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install -e .

# Make port 5051 available to the world outside this container
EXPOSE 5051

# Run app.py when the container launches
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5051"]
