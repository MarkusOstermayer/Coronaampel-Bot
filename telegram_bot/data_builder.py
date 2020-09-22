#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A Programm to ingest covid19 region-data into a sqlite-database for later use
"""

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

    logging.info(logg_const.TABLES_CREATED)

    # return the connection for later use
    return sqlite_connection


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


def insert_warnings(sql_connection, json_response):
    '''Function to insert the warning-levels into the warning-table'''

    for week in json_response['Kalenderwochen']:
        for region in week["Warnstufen"]:
            # Prepared statement to check if the region is already in the table
            # and order by desc revision to get the latest evrsion

            check_warn = db_const.CHECK_WARNING.format(region_id=region['GKZ'])

            result = execute_query(sql_connection, check_warn)

            if int(region['GKZ']) == 40101:
                print(result)
            # TODO: This should be simplified, since there are quite a few
            # things identical
            if len(result) == 0:
                # Check if the entry is already in the database and if not, it
                # will be inserted

                # Declare some variables for later use int eh query
                reason = "Null"
                level = int(region['Warnstufe'])
                region_id = int(region['GKZ'])
                kw = week['KW']

                # check if a reason for the alert_level was given, if so,
                # than set it
                if region['Begruendung'] != '':
                    reason = region['Begruendung']

                # Insert the first revision of the region to the database,
                # this is the starting-level
                warning_data = db_const.INSERT_WARNING.format(
                    revision=1, kw=kw, region_id=region_id, alert_level=level,
                    reason=reason)
                execute_query(sql_connection, warning_data)
            else:
                # It is already in the database, lets check if the warning
                # has changed from last time inserting it
                # result: (revision, kw, regions_id, alert_level, reason)
                if result[0][3] != int(region['Warnstufe']):
                    # define some variables we need to build the query
                    reason = "Null"
                    level = int(region['Warnstufe'])
                    region_id = int(region['GKZ'])
                    kw = week['KW']
                    rev = result[0][0] + 1

                    # check if a reason for the alert_level was given, if so,
                    # than set it
                    if region['Begruendung'] != '':
                        reason = region['Begruendung']

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


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''

    with open(const.CONFIG_FILE, "r") as file:
        configurations = json.loads(file.read())

    # create a database connection and build all the tables
    database_con = create_database(configurations["database_path"])

    json_response = get_corona_data()

    insert_regions(database_con, json_response)
    insert_warnings(database_con, json_response)

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
