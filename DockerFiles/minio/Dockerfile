FROM minio/minio:latest

COPY ./DockerFiles/minio/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]