FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip
RUN pip install python-telegram-bot==20.7 aiohttp

# Copy the rest of the app
COPY . .

# Run your bot
CMD ["python", "main.py"]
