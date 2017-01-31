FROM python:2.7.10

COPY . /srv

WORKDIR /srv

EXPOSE 5000

RUN pip install -r requirements.txt

CMD python morgenbot.py
