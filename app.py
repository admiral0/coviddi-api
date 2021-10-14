from typing import Optional, Callable, Any, Iterable, Mapping

from flask import Flask
from prometheus_client import start_http_server, Summary
from multiprocessing import Queue, Process
from threading import Thread
from queue import Empty
import os
import atexit

from gitcoviddi.repo import GitRepo, GitInfo
from gitcoviddi.loader import DataLoaderItaly

start_http_server(25000)
app = Flask(__name__, static_folder='static')

COVIDDI_REPO = os.getenv('COVIDDI_REPO', 'https://github.com/pcm-dpc/COVID-19.git')
COVIDDI_PATH = os.getenv('COVIDDI_HOME', os.path.join(os.getenv('HOME'), 'coviddimetro_data'))
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

INFO, DATA = updates.get(block=True)


class DataUpdater(Thread):
    def __init__(self, group: None = ..., target: Optional[Callable[..., Any]] = ..., name: Optional[str] = ...,
                 args: Iterable[Any] = ..., kwargs: Mapping[str, Any] = ..., *, daemon: Optional[bool] = ...) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.daemon = True

    def run(self) -> None:
        global INFO
        global DATA
        while True:
            INFO, DATA = updates.get(block=True)


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
