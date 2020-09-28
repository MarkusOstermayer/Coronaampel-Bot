#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A Programm to ingest covid19 region-data into a sqlite-database for later use
"""

import datetime
import json
import logging
import sqlite3

import requests

import constants as const
from constants import Database as db_const
from constants import Logging as logg_const
from utils import execute_query


def create_database(sql_path):
    """Creates the database connection and build the tables if necessary"""

    #  creation and connection to the database
    logging.info(logg_const.CREATING_DATABASE)
    sqlite_connection = sqlite3.connect(sql_path)
    logging.info(logg_const.DATABASE_CREATED)

    #  building the tables if necessary
    logging.info(logg_const.CREATING_TABLES)

    execute_query(sqlite_connection, db_const.CREATE_REGIONS_TABLE)
    execute_query(sqlite_connection, db_const.CREATE_WARNINGS_TABLE)
    execute_query(sqlite_connection, db_const.CREATE_USERS_TABLE)
    execute_query(sqlite_connection, db_const.CREATE_SUBSCRIPTIONS_TABLE)
    execute_query(sqlite_connection, db_const.CREATE_UPDATES_TABLE)
    execute_query(sqlite_connection, db_const.CREATE_TABLE_UPDATE_TIMES)

    logging.info(logg_const.TABLES_CREATED)

    # return the connection for later use
    return sqlite_connection


def get_corona_data(url):
    '''Get the data provided by the corona-ampel json file'''

    # create a get-request to the server to get the file
    req = requests.get(url)

    # read it and pare it as a text-file
    response_json = req.text
    json_response = json.loads(response_json)

    # return the parsed json-document
    return json_response


def insert_regions(sql_connection, json_response):
    '''Function to insert the region-data into the region-table'''

    # check if the number of entrys in the database matches the number of
    # entrys in the response
    lookup_regioncount = "Select Count(*) from regions"
    lookup_result = execute_query(sql_connection, lookup_regioncount)

    if lookup_result is not None:
        # if the result matches the number of regons in the file, than
        # there is nothing to ingest
        if lookup_result[0][0] == len(json_response["Regionen"]):
            logging.info(logg_const.NO_NEW_REGIONS)
            return

    logging.info(logg_const.NEW_REGIONS)

    # iterate over all items in the regions-set, this contains Bundesländer,
    # Gemeinden, Bezirke
    for region in json_response["Regionen"]:
        region_check = db_const.REGION_CHECK.format(id=int(region['GKZ']),
                                                    type=region['Region'],
                                                    name=region['Name'])

        # check if the region already exists in the database

        result = execute_query(sql_connection, region_check)

        # if not, it will be inserted
        if len(result) == 0:
            region_gkz = int(region['GKZ'])
            region_type = region['Region']
            region_name = region['Name']
            insert_region = db_const.INSERT_REGION.format(id=region_gkz,
                                                          type=region_type,
                                                          name=region_name)

            execute_query(sql_connection, insert_region)

            logging.info(
                logg_const.INSERT_SUCCESS.format(
                    region_name=region['Name']))

    return None


def insert_warnings(sql_connection, json_response, reverse_order=False):
    '''Function to insert the warning-levels into the warning-table'''

    inserted_warnings = False

    update_nr = len(json_response)



    if reverse_order:
        update_number_enumerator = reversed(range(0,update_nr))
    else:
        update_number_enumerator = range(0,update_nr)


    for update_number in update_number_enumerator:

        # get the date fromt he warningentry
        datestring = json_response[update_number]["Stand"]

        # check if the timestamp is already in the database
        lookup_quary = db_const.LOOKUP_UPDATE_TIME.format(
            datetimestring=datestring)

        result = execute_query(sql_connection, lookup_quary)

        if result[0][0] >= 1:
            print(result[0][0])
            # if the timestamp is in the database, continue with the next one
            logging.info(logg_const.TIMESTAMP_IN_DB.format(
                            datetimestring=datestring))
            continue
        else:
            print(result[0][0])
            
            # if not, it needs to be ingested and the updates need to be put
            # into the db
            logging.info(logg_const.TIMESTAMP_NOT_IN_DB.format(
                            datetimestring=datestring))
            insert_quary = db_const.INSERT_UPDATE_TIME.format(
                datetimestring=datestring)
            execute_query(sql_connection, insert_quary)

        for region in json_response[update_number]["Warnstufen"]:
            # Prepared statement to check if the region is already in the table
            # and order by desc revision to get the latest evrsion

            check_warn = db_const.CHECK_WARNING.format(region_id=region['GKZ'])

            result = execute_query(sql_connection, check_warn)

            # TODO: This should be simplified, since there are quite a few
            # things identical
            if len(result) == 0:
                # Check if the entry is already in the database and if not, it
                # will be inserted

                # Declare some variables for later use int eh query
                reason = "Null"
                level = int(region['Warnstufe'])
                region_id = int(region['GKZ'])

                date = datetime.datetime.strptime(datestring,
                    "%Y-%m-%dT%H:%M:%S%z").date()
                kw = date.isocalendar()[1]

                # Insert the first revision of the region to the database,
                # this is the starting-level
                warning_data = db_const.INSERT_WARNING.format(
                    revision=1, kw=kw, region_id=region_id, alert_level=level,
                    reason=reason)
                execute_query(sql_connection, warning_data)

                inserted_warnings = True
            else:
                # It is already in the database, lets check if the warning
                # has changed from last time inserting it
                # result: (revision, kw, regions_id, alert_level, reason)
                if result[0][3] != int(region['Warnstufe']):
                    # define some variables we need to build the query
                    reason = "Null"
                    level = int(region['Warnstufe'])
                    region_id = int(region['GKZ'])

                    date = datetime.datetime.strptime(datestring,
                        "%Y-%m-%dT%H:%M:%S%z").date()
                    kw = date.isocalendar()[1]

                    rev = result[0][0] + 1

                    # There is a new alert-level for the region, therefor we
                    # insert it with a new revision
                    warn_update = db_const.INSERT_WARNING.format(
                        revision=rev, kw=kw, region_id=region_id,
                        alert_level=level, reason=reason)
                    execute_query(sql_connection, warn_update)

                    # Add the region to the update-list for use by other
                    # programs
                    region_id = int(region['GKZ'])

                    add_update = db_const.ADD_UPDATE.format(
                        region_id=region_id)
                    execute_query(sql_connection, add_update)

    return inserted_warnings

def main():
    '''The main programmfunction, gats calles whenever the modul is run'''

    with open(const.CONFIG_FILE, "r") as file:
        configurations = json.loads(file.read())

    # create a database connection and build all the tables
    database_con = create_database(configurations["database_path"])

    json_regions = get_corona_data(const.CORONAKOMMISSIONV2)
    insert_regions(database_con, json_regions)

    json_warnings = get_corona_data(const.WARNSTUFEN_AKTUELL)
    inserted_warnings = insert_warnings(database_con, json_warnings)

    print(inserted_warnings)

    # close the database connection
    database_con.close()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s:%(levelname)s - %(message)s',
                        level=logging.INFO,
                        handlers=[
                            logging.FileHandler(const.DATA_BUILDER_LOG),
                            logging.StreamHandler()
                        ])
    main()
