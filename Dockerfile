FROM python:3.12

WORKDIR /src

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./src/ .

CMD ["fastapi", "run", "main.py", "--port", "80"]
