FROM python:3.6

RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN ls -l /code
RUN pip install -r requirements.txt

EXPOSE 9090
ENTRYPOINT ["/usr/local/bin/python3.6 /code/app.py"]