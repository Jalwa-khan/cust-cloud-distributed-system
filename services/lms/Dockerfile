FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /data
EXPOSE 5002
CMD ["gunicorn","--bind","0.0.0.0:5002","--workers","2","--threads","4","--timeout","120","--keep-alive","5","--worker-class","gthread","app:app"]
