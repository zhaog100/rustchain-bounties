FROM python:3.11-slim

WORKDIR /action

# Install dependencies
RUN pip install --no-cache-dir requests==2.31.0 PyGithub==2.1.1

# Copy action code
COPY reward.py /action/reward.py

# Set entrypoint
ENTRYPOINT ["python", "/action/reward.py"]
