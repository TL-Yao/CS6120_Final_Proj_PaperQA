FROM python:3.9

WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl && \
    curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x mc && \
    mv mc /usr/local/bin/

# install dependencies
COPY ./data_processor/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# copy entrypoint
COPY ./DockerFiles/data_processor/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh