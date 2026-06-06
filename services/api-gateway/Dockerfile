FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static/ ./static/
RUN mkdir -p /data
EXPOSE 5000
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","2","--threads","4","--timeout","120","--keep-alive","5","--worker-class","gthread","app:app"]
