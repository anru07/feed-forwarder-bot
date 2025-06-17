FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --upgrade pip
RUN pip install .

CMD ["python", "main.py"]
