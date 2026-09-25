# Версия задаётся в .python-version, CI передаёт её через --build-arg.
# Значение по умолчанию нужно для локальной сборки через docker compose.
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["python", "main.py"]
