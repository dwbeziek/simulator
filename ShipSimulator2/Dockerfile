FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
COPY ship_simulator.py /app/ship_simulator.py
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python3", "ship_simulator.py"]