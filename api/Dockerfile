FROM python:3.11

WORKDIR /src
COPY requirements.txt /src

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3", "-u", "main.py"]