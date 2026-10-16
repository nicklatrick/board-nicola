FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static ./static
ENV BOARD_DB=/app/data/board.db
VOLUME /app/data
EXPOSE 8001
CMD ["gunicorn","-b","0.0.0.0:8001","-w","2","app:app"]
