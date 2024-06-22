FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3.12 install -r requirements.txt
COPY . .
CMD ["python3", "main.py"]
