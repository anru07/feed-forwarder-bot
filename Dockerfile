# Use official Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of your app
COPY . .

# Start your bot
CMD ["python", "main.py"]
