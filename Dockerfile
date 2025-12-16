FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# PORT env var - Render will override this anyway
ENV PORT=8000

CMD ["python", "bot.py"]