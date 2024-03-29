import datetime
from typing import Optional, Callable, Any, Iterable, Mapping

from flask import Flask
from prometheus_client import start_http_server, Summary
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from multiprocessing import Queue, Process
from threading import Thread
from queue import Empty
import numpy as np
import os
import atexit

from werkzeug import Response

from gitcoviddi.repo import GitRepo, GitInfo
from gitcoviddi.loader import DataLoaderItaly

start_http_server(25000)
app = Flask(__name__, static_folder='static')

COVIDDI_REPO = os.getenv('COVIDDI_REPO', 'https://github.com/pcm-dpc/COVID-19.git')
COVIDDI_PATH = os.getenv('COVIDDI_HOME', os.path.join(os.getenv('HOME'), 'coviddimetro_data'))

INFLUX_HOST = os.getenv('INFLUX_HOST', "")
INFLUX_PORT = os.getenv('INFLUX_PORT', "")
INFLUX_ORG   = os.getenv('INFLUX_ORG', "coviddi")
INFLUX_TOKEN = os.getenv('INFLUXDB_TOKEN', "")

COVIDDI_REPO_DIR = 'Italy'

os.makedirs(COVIDDI_PATH, exist_ok=True)


def _keep_refreshing_repo(poison_pill: Queue, results: Queue, repo_url: str, repo_path: str):
    r = GitRepo(repo_url, repo_path)
    l = DataLoaderItaly(repo_path)
    results.put((r.info, l))
    done = False
    while not done:
        try:
            if r.poll():
                try:
                    l = DataLoaderItaly(repo_path)
                    results.put((r.info, l))
                except:
                    app.logger.warning('commit %s is bad', r.info.commit_id, exc_info=True)
            done = poison_pill.get(block=True, timeout=60*15)
        except Empty:
            pass
        except:
            app.logger.warning('could not pull from git', exc_info=True)


poison = Queue()
updates = Queue()
process = Process(
    target=_keep_refreshing_repo,
    args=(poison, updates, COVIDDI_REPO, os.path.join(COVIDDI_PATH, COVIDDI_REPO_DIR))
)
process.start()


def _cleanup():
    poison.put(True)
    process.join(timeout=10)


atexit.register(_cleanup)

INFO: GitInfo
DATA: DataLoaderItaly

INFO = GitInfo("none", datetime.datetime.fromtimestamp(0))
DATA = None


class DataUpdater(Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.db = None
        if len(INFLUX_HOST) > 0:
            self.db = InfluxDBClient(url=f"http://{INFLUX_HOST}:{INFLUX_PORT}",  token=INFLUX_TOKEN, org=INFLUX_ORG)
            self.write = self.db.write_api(write_options=SYNCHRONOUS)

    def update_influx(self):
        pp = []
        for date, fields in DATA.italy.to_dict('index').items():
            p = Point("italia")
            p.time(date.value)
            for k, v in fields.items():
                if type(v) is str:
                    p.tag(k, v)
                if not np.isnan(v):
                    p.field(k, v)
            pp.append(p)

        self.write.write("coviddi", "coviddi", pp)

    def run(self) -> None:
        global INFO
        global DATA
        while True:
            INFO, DATA = updates.get(block=True)
            if self.db is not None:
                self.update_influx()


updater_thread = DataUpdater()
updater_thread.start()


class NotReadyMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if DATA is None:
            res = Response(u'Loading', mimetype='text/plain', status=503)
            return res(environ, start_response)
        return self.app(environ, start_response)


app.wsgi_app = NotReadyMiddleware(app.wsgi_app)


@app.route('/api/android/v1/')
def android_api_v1():
    r = app.response_class(
        response=DATA.android_bundle_v1,
        status=200,
        mimetype='application/json'
    )
    return r


@app.route('/api/v1/italy')
def api_v1_italy():
    response = app.response_class(
        response=DATA.italy,
        status=200,
        mimetype='text/csv'
    )
    response.headers['X-Commit-Id'] = INFO.commit_id
    response.headers['X-Last-Updated'] = INFO.commit_time.timestamp()
    return response


@app.route('/api/v1/regioni')
def api_v1_regioni():
    response = app.response_class(
        response=DATA.regions,
        status=200,
        mimetype='text/csv'
    )
    response.headers['X-Commit-Id'] = INFO.commit_id
    response.headers['X-Last-Updated'] = INFO.commit_time.timestamp()
    return response


@app.route('/api/v1/province')
def api_v1_province():
    response = app.response_class(
        response=DATA.regions,
        status=200,
        mimetype='text/csv'
    )
    response.headers['X-Commit-Id'] = INFO.commit_id
    response.headers['X-Last-Updated'] = INFO.commit_time.timestamp()
    return response


@app.route('/api/v1/status')
def api_v1_status():
    return {
        'status': 'ok',
        'last_update': INFO.commit_time.timestamp(),
        'commit_id': INFO.commit_id,
    }


if __name__ == '__main__':
    app.run()
