# Use the official Python base image
FROM python:latest

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code to the container
COPY . .

# Run migrations
RUN python manage.py migrate

# Expose the application port
EXPOSE 8000

