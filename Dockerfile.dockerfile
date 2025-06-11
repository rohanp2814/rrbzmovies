# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy and install dependencies first for better caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all files from current directory to container
COPY . .

# Download NLTK data needed by your bot (modify if your bot uses other nltk datasets)
RUN python -m nltk.downloader punkt

# Command to run your bot script
CMD ["python", "smart_search_bot.py"]
