FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# デフォルトでは sender を起動する
CMD ["python", "send_dnp3_with_oob_trace.py"]
