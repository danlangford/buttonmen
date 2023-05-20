FROM python:3-alpine
WORKDIR /app
COPY . .
RUN python3 -m pip install -r requirements.txt
CMD [ "python3", "./mmr.py" ]
