FROM python:3.12-alpine

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
EXPOSE 8000

COPY main.py /main.py
COPY templates/ /templates/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
