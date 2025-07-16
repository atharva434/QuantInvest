FROM python:3.9-slim

# Avoid Python writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && apt-get clean

# Set working directory
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /code/

# Add and set permissions for the entrypoint script

# Run the entrypoint script on container start
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 127.0.0.1:8000"]