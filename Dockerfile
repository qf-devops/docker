FROM python:3.4-alpine
# Set environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ADD . /code
WORKDIR /code
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
