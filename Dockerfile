FROM python:3.11-slim

WORKDIR /app

# System deps (rarely changes — cached layer)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Python deps (changes occasionally)
COPY pyproject.toml .
# Need a minimal dunham package for pip install to succeed
RUN mkdir -p dunham && echo '__version__ = "0.1.0"' > dunham/__init__.py
RUN pip install --no-cache-dir .

# Pre-download whisper model (large, cached layer)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"

# App code (changes frequently — last layer)
COPY dunham/ dunham/

ENTRYPOINT ["dunham"]
