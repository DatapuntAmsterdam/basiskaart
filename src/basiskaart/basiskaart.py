# -*- coding: utf-8 -*-

import logging
import os
import shutil
import zipfile
from io import BytesIO

from objectstore.objectstore import ObjectStore

from basiskaart.basiskaart_setup import VALUES
from sql_utils.sql_utils import SQLRunner, createdb

log = logging.getLogger(__name__)
sql = SQLRunner()


def fill_basiskaart(tmpdir, schema):
    """
    Importeer 'basiskaart files' in Postgres
    schema 'basiskaart' mbv ogr2ogr
    :return:
    """

    createdb()
    os.makedirs(tmpdir, exist_ok=True)

    log.info("Clean existing schema {}".format(schema))
    sql.run_sql("DROP SCHEMA IF EXISTS {} CASCADE".format(schema))
    sql.run_sql("CREATE SCHEMA {}".format(schema))
    sql.import_basiskaart(tmpdir, schema)
    if schema == 'bgt':
        renamefields()


def renamefields():
    fieldmapping = {
                    'bagbolgst':    'id_bagvbolaagste_huisnummer',
                    'bagid':	    'BAG_identificatie',
                    'bagoprid':     'identificatieBAGOPR',
                    'bagpndid':     'identificatieBAGPND',
                    'bagvbohgst':   'identificatieBAGVBOHoogsteHuisnummer',
                    'bagvbolgst':   'identificatieBAGVBOLaagsteHuisnummer',
                    'begintijd':    'objectbegintijd',
                    'bgtfunctie':   'bgt_functie',
                    'bgtfysvkn':    'bgt_fysiekvoorkomen',
                    'bgtnagid':     'bgt_nummeraanduidingreeks_id',
                    'bgtorlid':     'bgt_openbareruimtelabel_id',
                    'bgtpndid':     'bgt_pand_id',
                    'bgtstatus':    'bgt_status',
                    'bgttype':      'bgt_type',
                    'bij_object':   'hoortbij',
                    'bronhoud':     'bronhouder',
                    'eindreg':      'eindregistratie',
                    'eindtijd':     'objecteindtijd',
                    'einddtijd':    'objecteindtijd',
                    'geom':         'geometrie',
                    'hm_aand':      'hectometeraanduiding',
                    'hoogtelig':    'relatievehoogteligging',
                    'hoortbij':     'hoortbijtypeoverbrugging',
                    'inonderzk':    'inonderzoek',
                    'isbeweegb':    'overbruggingisbeweegbaar',
                    'labeltekst':   'label_tekst',
                    'lokaalid':     'identificatie_lokaalid',
                    'lv_pubdat':    'lv_publicatiedatum',
                    'namespace':    'identificatie_namespace',
                    'oprtype':      'openbareruimtetype',
                    'plusfunct':    'plus_functie',
                    'plusfysvkn':   'plus_fysiekvoorkomen',
                    'plusstatus':   'plus_status',
                    'plustype':     'plus_type',
                    'tijdreg':      'tijdstipregistratie',
                    }
    tables_in_schema = sql.gettables_in_schema('bgt')
    for t in tables_in_schema:
        table = '"bgt"."{}"'.format(t[2])
        columns = sql.get_columns_from_table(table)
        renames = [(col, fieldmapping[col]) for col in columns if col in fieldmapping]
        for fromcol, tocol in renames:
            sql.rename_column(table, fromcol, tocol)


def get_basiskaart(object_store_name, name, tmpdir, prefix, importnames,
                   endswith):
    """
    Get zip from either local disk (for testing purposes) or from Objectstore

    :param object_store_name: Username to objectstore
    :param name: Name of directory where zipfiles are
    :param tmpdir: temporary storage where to extract
    :param prefix: Prefix in objectstore
    :param importnames: First (glob) characters of names of zipfiles
    :param endswith: Name of the importfile endswith
    :return: None
    """
    try:
        shutil.rmtree(tmpdir)
    except FileNotFoundError:
        pass
    else:
        log.info("Removed {}".format(tmpdir))

    store = ObjectStore(prefix, object_store_name)
    files = store.get_store_objects(name)
    log.info("Download shape files zip into '{}'".format(tmpdir))

    for file in files:
        fsplit = os.path.split(file['name'])
        if len(fsplit) == 2 and fsplit[1].startswith(importnames) and \
                fsplit[1].endswith(endswith):
            content = BytesIO(store.get_store_object(file['name']))
            inzip = zipfile.ZipFile(content)
            log.info("Extract %s to temp directory %s", file['name'], tmpdir)
            inzip.extractall(tmpdir)


def process_basiskaart(kbk_name):
    for object_store_name, tmpdir, path, prefix, importnames, schema, endswith \
            in VALUES[kbk_name]:
        get_basiskaart(object_store_name, path, tmpdir, prefix, importnames,
                       endswith)
        fill_basiskaart(tmpdir, schema)
