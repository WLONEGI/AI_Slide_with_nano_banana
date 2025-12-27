FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for potential PDF/Office tools (as per requirements)
# 'libreoffice' and 'poppler-utils' are heavy, but required for full PPTX handling feature if we were to implementing it fully.
# For this prototype, we'll keep it lighter but include basic build tools.
RUN apt-get update && apt-get install -y \
    build-essential \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 8000

# Run commands
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
