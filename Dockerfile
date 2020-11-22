FROM python:3.8

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app
VOLUME ['/coviddi']
ENV COVIDDI_HOME="/coviddi"
EXPOSE 5000
ENTRYPOINT [ "/usr/local/bin/python"]
CMD ["app.py"]