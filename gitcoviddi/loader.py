import pandas
import numpy
import json
from os import path

DIFFS = {
    'ricoverati_con_sintomi',
    'terapia_intensiva',
    'isolamento_domiciliare',
    'nuovi_positivi',
    'dimessi_guariti',
    'deceduti',
    'casi_da_sospetto_diagnostico',
    'casi_da_screening',
    'totale_casi',
    'tamponi',
    'casi_testati',
}

class DataLoaderItaly:
    def __init__(self, repo_path):
        converters = {
            'data': pandas.to_datetime
        }
        nation = pandas.read_csv(
            path.join(repo_path, 'dati-andamento-nazionale','dpc-covid19-ita-andamento-nazionale.csv'),
            index_col='data',
            converters=converters
        )
        regions = pandas.read_csv(
            path.join(repo_path, 'dati-regioni', 'dpc-covid19-ita-regioni.csv'),
            index_col='data',
            converters=converters
        )
        provinces = pandas.read_csv(
            path.join(repo_path, 'dati-province', 'dpc-covid19-ita-province.csv'),
            index_col='data',
            converters=converters
        )

        for df in (nation, regions, provinces):
            for field in DIFFS:
                if field in df:
                    df[field + '_dt'] = df[field].diff()


        bundle = {
            'italia': nation.replace({numpy.nan: None}).to_dict('records'),
            'regioni': regions.replace({numpy.nan: None}).to_dict('records'),
            'province': provinces.replace({numpy.nan: None}).to_dict('records'),
        }

        self.android_bundle_v1 = json.dumps(bundle)
        self.italy = nation.to_csv()
        self.regions = regions.to_csv()
        self.provinces = provinces.to_csv()

