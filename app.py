from typing import Optional, Callable, Any, Iterable, Mapping

import os
import signal
import time

from influxdb import InfluxDBClient

from gitcoviddi.repo import GitRepo, GitInfo
from gitcoviddi.loader import DataLoaderItaly

import numpy as np

COVIDDI_REPO = os.getenv('COVIDDI_REPO', 'https://github.com/pcm-dpc/COVID-19.git')
COVIDDI_PATH = os.getenv('COVIDDI_HOME', os.path.join(os.getenv('HOME'), 'coviddimetro_data'))
INFLUX_HOST = os.getenv('INFLUX_HOST', "")
INFLUX_PORT = os.getenv('INFLUX_PORT', "")
INFLUX_DB = os.getenv('INFLUX_DB', "coviddi")
INFLUX_USER = os.getenv('INFLUXDB_USER', "")
INFLUX_PASS = os.getenv('INFLUXDB_USER_PASSWORD', "")

COVIDDI_REPO_DIR = 'Italy'
RUN_PLS = True

os.makedirs(COVIDDI_PATH, exist_ok=True)

def signal_handler(signal, frame):
    global RUN_PLS
    RUN_PLS = False
    print("Exiting")

signal.signal(signal.SIGINT, signal_handler)


def main():
    repo_path = os.path.join(COVIDDI_PATH, COVIDDI_REPO_DIR)
    print("Reading repo....")
    r = GitRepo(COVIDDI_REPO, repo_path)
    r.poll()
    current_commit = r.info.commit_id
    print(f"repo at {current_commit}")
    time.sleep(10)
    update(repo_path)

    while RUN_PLS:
        r.poll()
        if current_commit == r.info.commit_id:
            time.sleep(10)
            continue
        print(f"{r.info.commit_time} - Updated repo from {current_commit} to {r.info.commit_id}")
        current_commit = r.info.commit_id
        update(repo_path)


def update(path):
    l = DataLoaderItaly(path)
    with open(os.path.join(COVIDDI_PATH, "android.v1.json"), "w") as fp:
        print("Writing android bundle")
        fp.write(l.android_bundle_v1)
    if INFLUX_HOST != "":
        print("Saving to influx")
        save(l)




def save(l: DataLoaderItaly):
    db = InfluxDBClient(INFLUX_HOST, int(INFLUX_PORT), INFLUX_USER, INFLUX_PASS, INFLUX_DB)
    db.switch_database(INFLUX_DB)

    pp = []
    for date, fields in l.italy.to_dict('index').items():
        add_fields = {}
        for k,v in fields.items():
            if type(v) is str:
                continue
            if not np.isnan(v):
                add_fields[k]=int(v)
        #print(add_fields)
        pp.append({
            "measurement": 'italia',
            "time": int(date.value),
            "fields": add_fields
        })
    

    db.write_points(pp)
    #db.write_points(l.regions, 'regioni')
    #db.write_points(l.provinces, 'province')


if __name__ == '__main__':
    main()
