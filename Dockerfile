FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --upgrade "pip>=26.2.2" \
    && pip install --no-cache-dir -r requirements.txt
# RUN python -m pip install "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
#      && pip install --no-cache-dir -r requirements.txt


COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# docker build -t rewrapped .
# docker run -d --env-file .env -p 8000:8000 rewrapped