FROM python:3.9

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app
VOLUME ['/coviddi']
ENV COVIDDI_HOME="/coviddi"
EXPOSE 5000 25000
ENTRYPOINT [ "uwsgi"]
CMD ["--http", "0.0.0.0:5000", "--module", "app:app"]
