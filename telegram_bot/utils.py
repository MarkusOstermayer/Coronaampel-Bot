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

from telegram import InlineKeyboardButton
from constants import Database as db_const
from constants import TelegramConstants as tele_const


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


def region_cmd_buttons(sel_conn, query, cmd_prefix):
    """
    Returns a list of inlinekeyboardbuttons that are used to ask the users
    about cities
    """
    result = execute_query(sel_conn, query)

    # If the result-tuple is empty, than there are not regions
    # called the way the suer put it in
    if(len(result) == 0):
        return None
    # If it is not empty, than we have regions we can print to the screen
    # and let the user choose
    else:
        # list to store all buttons
        region_keyboard = []

        # itterate over the result, creating a button for each region
        for item in result:
            # create a command that is send back to the callbacl quary handler
            # and gets prozessed there
            command = "{cmd_prefix}_{name}_{id}".format(cmd_prefix=cmd_prefix,
                                                        name=str(item[1]),
                                                        id=str(item[0]))

            # with the command create the button with the name of the region
            # as button text
            button = InlineKeyboardButton(text=str(item[0]),
                                          callback_data=command)

            # append the button to the list of buttons
            region_keyboard.append([button])

        # add a button to cancel the current operation
        button = InlineKeyboardButton(
                    text=tele_const.CMD_PREFIX_CANCEL,
                    callback_data=tele_const.CMD_PREFIX_CANCEL)

        # append the button to the list of buttons
        region_keyboard.append([button])

        # return the created list of buttons
        return region_keyboard


def simple_js_parser(pagecontent):
    """
    Simple parsing-function for parsing js-data from the corona-dashboard
    """
    # create an empty dictionarry
    variables = {}

    # get each line, stripping away any leading or ending newline
    lines = pagecontent.strip("\n").split("\n")

    # iterate over the lines
    for line in lines:
        # removing every var-word and replacing it with nothing, afterwards
        # splitting by the =-Operator surrounded by two spaces
        # TODO: Check if " = " nessesarry or if splitting by = and stripping
        # works
        line_data = line.replace("var", "").split(" = ")

        variables[line_data[0].strip()] = ast.literal_eval(
            line_data[1].strip(";"))

    return variables

def string_assembler(data, version_date, total, lookup=None, ordered = False,
                    max_lable_alignment=5):
    '''Used to create a textstring which represends numeric data'''

    # create the output-string
    o_str = ""

    # check if the data has to be ordered by value
    if ordered:
        # create a dict out of key and data
        new_dict = {}

        # fill the dict
        for item in data:
            new_dict[item["label"]] = item["y"]

        # cretae a lsit out of the dict and insert-sort the data
        # ref. https://stackoverflow.com/questions/613183/how-do-i-sort-a-
        # dictionary-by-value
        data = [{"label": k, "y" : v} for k, v in sorted(new_dict.items(),
            key=lambda item: item[1])]

    # Check if a lookup-dict has to be used in order to translate the keys
    if lookup is None:
        # check what the longest lable in the list is
        max_lable_len = max([len(x["label"]) for x in data])
    else:
        # if so, check what the maximal linelenth is according to the
        # lookup-dict
        max_lable_len = max([len(x) for x in lookup.values()])

    # check ig the max_linelength is greater than the maximum alignment
    if max_lable_len > max_lable_alignment:
        max_lable_len = max_lable_alignment

    # iterate over each subdict
    for item in data:
        # check if the lable ahs to be translated
        if lookup is None:
            label = item["label"]

        else:
            label = lookup[item["label"]]

        # ajust the textallignment according to the max lablenegth

        label = label.ljust(max_lable_len)
        # calculate the percentage-value
        percent = (100 / (total / int(item["y"])))
        # build the string and append it to the rest
        o_str += "{}: {:>5} ({:>4.2f}%)\n".format(label,item["y"], percent)

    # append a versionnumber
    o_str += "Version: {}".format(version_date)

    return o_str

def string_assembler(data, version_date, total, lookup=None, ordered=False,
                     max_lable_alignment=5):
    '''Used to create a textstring which represends numeric data'''

    # create the output-string
    o_str = ""

    # check if the data has to be ordered by value
    if ordered:
        # create a dict out of key and data
        new_dict = {}

        # fill the dict
        for item in data:
            new_dict[item["label"]] = item["y"]

        # cretae a lsit out of the dict and insert-sort the data
        # ref. https://stackoverflow.com/questions/613183/how-do-i-sort-a-
        # dictionary-by-value
        data = [{"label": k, "y": v} for k, v in sorted(
                new_dict.items(),
                key=lambda item: item[1])]

    # Check if a lookup-dict has to be used in order to translate the keys
    if lookup is None:
        # check what the longest lable in the list is
        max_lable_len = max([len(x["label"]) for x in data])
    else:
        # if so, check what the maximal linelenth is according to the
        # lookup-dict
        max_lable_len = max([len(x) for x in lookup.values()])

    # check ig the max_linelength is greater than the maximum alignment
    if max_lable_len > max_lable_alignment:
        max_lable_len = max_lable_alignment

    # iterate over each subdict
    for item in data:
        # check if the lable ahs to be translated
        if lookup is None:
            label = item["label"]

        else:
            label = lookup[item["label"]]

        # ajust the textallignment according to the max lablenegth

        label = label.ljust(max_lable_len)
        # calculate the percentage-value
        percent = (100 / (total / int(item["y"])))
        # build the string and append it to the rest
        o_str += "{}: {:>5} ({:>4.2f}%)\n".format(label, item["y"], percent)

    # append a versionnumber
    o_str += "Version: {}".format(version_date.split("V")[0])

    return o_str


# Keep the data in the cache, which will get reset every hour
@lru_cache(maxsize=32)
def get_data_js(url):
    """
    Used to get the interpreted json data from the dashbaord
    """
    page = requests.get(url).text
    result = simple_js_parser(page)
    return result
