FROM python:3.12

# Set working directory inside the container
WORKDIR /app

# Copy dependency list first so Docker can cache installs
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY server.py .

# Expose port for MCP server
EXPOSE 8080

# Start MCP server
CMD ["python", "server.py"]