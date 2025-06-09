FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["streamlit", "run", "dashboard.py", "--server.port=${PORT}", "--server.enableCORS=false"]
