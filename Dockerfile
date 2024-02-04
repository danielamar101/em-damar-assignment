FROM python:3.11-slim

WORKDIR /app

COPY . /app

# install deps
RUN pip install -r requirements.txt

# Create a new unpriviledged user such that nothing has access to our precious docker socket
RUN adduser --disabled-password --gecos '' em-unpriviledged
USER em-unpriviledged

EXPOSE 4545

CMD ["python", "main.py"]
