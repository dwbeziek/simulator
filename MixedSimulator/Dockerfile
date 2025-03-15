FROM python:3.10-slim
WORKDIR /app
COPY fmc230_simulator.py /app/fmc230_simulator.py
RUN pip install paho-mqtt==1.6.1  # Your version
CMD ["python3", "fmc230_simulator.py"]