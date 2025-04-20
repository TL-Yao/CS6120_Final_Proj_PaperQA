#!/bin/bash

while true; do
    echo "Start processing paper data..."
    RESPONSE=$(curl --request GET \
        --url http://localhost:8000/embedding_file \
        -w "\n%{http_code}" \
        -s)


    RESPONSE_CODE=$(tail -n1 <<< "$RESPONSE")
    RESPONSE_BODY=$(sed '$ d' <<< "$RESPONSE")

    echo "Response code = ${RESPONSE_CODE}"
    echo "Response body = ${RESPONSE_BODY}"


    if [ "$RESPONSE_CODE" -ne 200 ]; then
        echo "Non-200 status code received, exiting loop."
        break
    fi

    echo "One paper data successfully processed, checking again..."
    sleep 1
done