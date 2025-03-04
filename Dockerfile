FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY fmc230_simulator.py .

CMD ["python", "fmc230_simulator"]