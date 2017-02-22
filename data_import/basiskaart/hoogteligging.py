import logging
import os

from openpyxl import load_workbook

from sql_utils import SQLRunner

log = logging.getLogger(__name__)

XLS_VIEWDEF = os.path.dirname(
    os.path.realpath(__file__)) + '/fixtures/wms_kaart_database.xlsx'

sql = SQLRunner()


def create_views_based_on_workbook():
    view_definitions = read_workbook()
    min_max_values = get_min_max_value(view_definitions)
    create_view(view_definitions, min_max_values)


def read_workbook():
    view_definitions = {}
    wb = load_workbook(XLS_VIEWDEF)
    startvalue = 1
    for idx, row in enumerate(wb['Blad1'].rows):
        rowvalues = [r.value for r in row]
        schema, tabel, categorie, geotype, viewnm, vwattr, laag, grp, \
            minhoogte, maxhoogte = rowvalues

        if idx >= startvalue:
            viewname = '"{}"."{}_{}<hoogteligging>"'.format(schema.lower(),
                                                            categorie, geotype)
            if sql.table_exists(schema.lower(), tabel):
                if viewname not in view_definitions:
                    view_definitions[viewname] = []
                view_definitions[viewname] += [
                    [schema.lower(), tabel, vwattr, minhoogte, maxhoogte]]
            else:
                log.error("Table {} in view {} does not exist".format(tabel,
                                                                      viewname))
    return view_definitions


def get_min_max_value(view_definitions):
    min_max_values = {}
    for viewname, viewdef in view_definitions.items():
        for viewrow in viewdef:
            minvalue = viewrow[3]
            maxvalue = viewrow[4]
            if viewname not in min_max_values:
                min_max_values[viewname] = [0, 0]
            if min_max_values[viewname][0] > minvalue:
                min_max_values[viewname][0] = minvalue
            if min_max_values[viewname][1] < maxvalue:
                min_max_values[viewname][1] = maxvalue
    return min_max_values


def create_view(view_definitions, min_max_values):
    for viewname, viewdef in view_definitions.items():
        minvalue = min_max_values[viewname][0]
        maxvalue = min_max_values[viewname][1]

        build_view_per_name(viewname, viewdef, minvalue, maxvalue)


def build_view_per_name(viewname, viewdef, minvalue, maxvalue):
    new_viewdef = []
    for schema, tabel, vwattr, minval, maxval in viewdef:
        new_viewdef.append([schema,
                            tabel,
                            define_fields(tabel, schema, vwattr),
                            minval,
                            maxval])

    create_views(viewname, new_viewdef, minvalue, maxvalue)


def create_views(viewname, viewdef, minvalue, maxvalue):
    viewstmt = "CREATE OR REPLACE VIEW {} AS {}"
    single_select = 'SELECT {} FROM "{}"."{}" WHERE hoogtelig = {}'

    for hoogte in range(minvalue, maxvalue):
        selects = []

        for schema, tabel, vwattr, minval, maxval in viewdef:
            selects.append(
                single_select.format(vwattr, schema, tabel, hoogte))

        real_viewname = viewname.replace('<hoogteligging>',
                                         str(hoogte).replace('-', '_'))
        sql.run_sql(viewstmt.format(real_viewname, " UNION ".join(selects)))


def define_fields(tabel, schema, vwattr):
    sql_table_name = '"{}"."{}"'.format(schema, tabel)
    foundcolumns = sql.get_columns_from_table(sql_table_name)
    required_columns = [field.strip() for field in vwattr.split(',')]
    columns_not_found = [column for column in required_columns if
                         column not in foundcolumns]

    for not_found in columns_not_found:
        vwattr = vwattr.replace(not_found, 'NULL as ' + not_found)

    return vwattr
