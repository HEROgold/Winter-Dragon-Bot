FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3.12 install -r requirements.txt

COPY /bot /bot
COPY /database /database
COPY /tools /tools
COPY main.py main.py
COPY pyproject.toml pyproject.toml

CMD ["python3", "main.py"]
