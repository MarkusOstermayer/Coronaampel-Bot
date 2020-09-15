#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A utility file for the coronaampel-bot project
"""

import ast
from functools import lru_cache
import logging
import requests
import sqlite3

from constants import Database as db_const


def execute_query(connection, query):
    '''Execute Quarry's on the database'''

    # get a cursor on the database to work with it
    cursor = connection.cursor()
    result = None
    try:
        # execute the provided quarry on the database, commiting and logging
        cursor.execute(query)
        result = cursor.fetchall()
        logging.info(db_const.QUERY_EXECUTED.format(quary=query))

    # throws an exception if something wrong was done, ether by violation
    # of a database contraint or by an invalid quarry
    except sqlite3.DatabaseError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(exc_name=db_const.DB_ERROR,
                                                    quary=query))
        logging.exception(exception)

    except sqlite3.OperationalError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(exc_name=db_const.OP_ERROR,
                                                    quary=query))
        logging.exception(exception)

    connection.commit()
    return result


def simple_js_parser(pagecontent):
    """
    Simple parsing-function for parsing js-data from the corona-dashboard
    """
    variables = {}

    lines = pagecontent.strip("\n").split("\n")

    for line in lines:
        line_data = line.replace("var", "").split(" = ")

        # print(line_data)
        variables[line_data[0].strip()] = ast.literal_eval(
            line_data[1].strip(";"))
    return variables


@lru_cache
def get_data_js(url):
    """
    Used to get the interpreted json data from the dashbaord
    """
    page = requests.get(url).text
    result = simple_js_parser(page)
    return result
