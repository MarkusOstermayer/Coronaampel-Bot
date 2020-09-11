#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A utility file for the coronaampel-bot project
"""

import logging
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
