FROM python:3.12-alpine

WORKDIR /app

COPY app/server.py app/index.html ./

EXPOSE 8080

CMD ["python", "/app/server.py"]

