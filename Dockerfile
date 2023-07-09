FROM python:3.11
WORKDIR /notes
COPY dist/notes*.whl .
ENV DATA_PATH=/data/
RUN \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade notes*.whl
CMD ["notes", "server", "--host", "0.0.0.0", "--port", "80"]
