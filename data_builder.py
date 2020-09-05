# !/usr/bin/python3
#  -*- coding: utf-8 -*-

"""
A Programm to ingest covid19 region-data into a sqlite-database for later use
"""

__copyright__ = "Copyright 2020"

import logging
import json
import sqlite3
import requests


import constants as const
from constants import DATABASE as db_const
from constants import Logging as logging_const


def create_database():
    """Creates the database conenction and build the tables if nessesary"""

    #  creation and conenction to the database
    logging.info("Creating database ...")
    sqlite_connection = sqlite3.connect("corona_db.sqlite")
    logging.info("Database created!")

    #  building the tables if nessesary
    logging.info("Creating tables ...")
    execute_query(sqlite_connection, const.CREATE_REGIONS_TABLE)
    execute_query(sqlite_connection, const.CREATE_WARNINGS_TABLE)
    execute_query(sqlite_connection, const.CREATE_USERS_TABLE)
    execute_query(sqlite_connection, const.CREATE_SUBSCRIPTIONS_TABLE)
    execute_query(sqlite_connection, const.CREATE_UPDATES_TABLE)
    logging.info("Tables created!")

    # return the connection for later use
    return sqlite_connection


def execute_query(connection, query):
    '''Execute Quarrys on the dabasase'''

    # get a cursor on the database to work with it
    cursor = connection.cursor()

    try:
        # execute the provided quarry on the database, commiting and logging
        cursor.execute(query)
        connection.commit()
        logging.info(db_const.QUERY_EXECUTED.format(query))

    # throws an exception if something wrong was done, ether by violation
    # of a database contraint or by an invalid quarry
    except sqlite3.DatabaseError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(db_const.DB_ERROR, query))
        logging.exception(exception)

    except sqlite3.OperationalError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(db_const.OP_ERROR, query))
        logging.exception(exception)


def get_corona_data():
    '''Get the data provided by the corona-ampel json file'''

    # create a get-request to the server to get the file
    req = requests.get(const.CORONAKOMMISSIONV2)
    # read it and pare it as a text-file
    response_json = req.text
    json_response = json.loads(response_json)

    # return the parsed json-document
    return json_response


def insert_regions(sql_connection, json_response):
    '''Function to insert the region-data into the region-table'''

    # get a cursor to work on the database and to execute quarys
    cursur = sql_connection.cursor()
    # iterate over all items in the regions-set, this contains Bundesländer,
    # Gemeinden, Bezirke
    for region in json_response["Regionen"]:
        region_data = (int(region['GKZ']),
                       region['Region'],
                       region['Name'])
        # check if the region already exists in the database
        cursur.execute(db_const.REGION_CHECK,
                       region_data)
        result = cursur.fetchone()
        # if not, it will be inserted
        if result is None:
            execute_query(sql_connection,
                          db_const.INSERT_REGION.format(region_data))

            logging.info(logging_const.INSERT_SUCCESS.format(region['Name']))


def insert_warnings(sql_connection, json_response):
    '''Function to insert the warninglevels into thewarning-table'''

    # get a cursor to work on the database and to isnert and execute quarrys
    cursur = sql_connection.cursor()
    for week in json_response['Kalenderwochen']:
        for region in week["Warnstufen"]:
            # Prepared statement to check if the region is already in the table
            # and order by desc revision to get the latest evrsion

            cursur.execute(db_const.CHECK_WARNING, (region['GKZ'],))
            result = cursur.fetchone()
            if result is None:
                # Check if the entry is already in the database and if not, it
                # will be inserted
                if region['Begruendung'] == '':
                    begruendung = "Null"
                else:
                    begruendung = region['Begruendung']
                warning_data = (1,
                                week['KW'],
                                int(region['GKZ']),
                                int(region['Warnstufe']),
                                begruendung)
                execute_query(sql_connection,
                              db_const.INSERT_WARNING.format(warning_data))
            else:
                # It is already in the database, lets check if the warning
                # has changed from last time inserting it
                # result: (revision, kw, regions_id, alert_level, reason)
                if result[3] != int(region['Warnstufe']):
                    if region['Begruendung'] == '':
                        begruendung = "Null"
                    else:
                        begruendung = region['Begruendung']
                    # There is a new alertlevel for the region, therefor we
                    # insert it with a new revision
                    region_update = (result[0] + 1,  # increent the revision
                                     week['KW'],
                                     int(region['GKZ']),
                                     int(region['Warnstufe']),
                                     begruendung)
                    execute_query(sql_connection,
                                  db_const.INSERT_WARNING.format(region_update)
                                  )

                    region_id = int(region['GKZ'])
                    execute_query(sql_connection,
                                  db_const.ADD_UPDATE.format(region_id))


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''
    # create a database conenction and build all the tables
    database_con = create_database()

    json_response = get_corona_data()

    insert_regions(database_con, json_response)
    insert_warnings(database_con, json_response)
    '''
    str = """{
        "Kalenderwochen": [{
        "KW": 36,
        "Warnstufen": [{
            "GKZ": "0",
            "Warnstufe": "10",
            "Begruendung": ""
        }]
    }]}
    """
    insert_warnings(database_con, json.loads(str))
    str = """{
        "Kalenderwochen": [{
        "KW": 36,
        "Warnstufen": [{
            "GKZ": "0",
            "Warnstufe": "10",
            "Begruendung": ""
        }]
    }]}
    """
    insert_warnings(database_con, json.loads(str))
    insert_warnings(database_con, json.loads(str))
    '''

    # clsoe the database connection
    database_con.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(filename='corona_bot.log',
                        filemode='w',
                        format='%(name)s - %(levelname)s -  %(message)s')
    main()
