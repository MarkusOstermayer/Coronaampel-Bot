# !/usr/bin/python3
#  -*- coding: utf-8 -*-

"""
A telegram-bot to inform about updates of the corona-ampel
"""

__copyright__ = "Copyright 2020"

import json
import logging
import sqlite3

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler

from constants import TelegramConstants as tele_const
from constants import DATABASE as db_const


def execute_query(connection, query):
    '''Execute Quarrys on the dabasase'''

    # get a cursor on the database to work with it
    cursor = connection.cursor()
    result = None
    try:
        # execute the provided quarry on the database, commiting and logging
        cursor.execute(query)
        result = cursor.fetchall()
        logging.info(db_const.QUERY_EXECUTED.format(query))

    # throws an exception if something wrong was done, ether by violation
    # of a database contraint or by an invalid quarry
    except sqlite3.DatabaseError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(db_const.DB_ERROR, query))
        logging.exception(exception)

    except sqlite3.OperationalError as exception:
        logging.error(db_const.EXCEPTION_MSG.format(db_const.OP_ERROR, query))
        logging.exception(exception)

    connection.commit()
    return result


class TelegramBot():
    '''Class for the telegram-bot'''
    def __init__(self):
        with open("config.json", "r") as file:
            result = json.loads(file.read())
        updater = Updater(token=result["telegram-token"], use_context=True)
        dispatcher = updater.dispatcher

        # Telegram-Commandhandler
        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('subscribe',
                                              self.subscribe_to_region))
        dispatcher.add_handler(CommandHandler('unsubscribe',
                                              self.unsubscribe_from_regions))
        dispatcher.add_handler(CommandHandler('showsubscriptions',
                                              self.list_all_regions))

        dispatcher.add_handler(CallbackQueryHandler(self.command_handler))

        # connect to the database
        self.sqlite_connection = sqlite3.connect("corona_db.sqlite",
                                                 check_same_thread=False)

        updater.start_polling()

        #  Block until the you presses Ctrl-C or the process receives SIGINT,
        #  SIGTERM or SIGABRT. This should be used most of the time, since
        #  start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()

    def command_handler(self, update, context):
        '''USed to ahndle commandas, send by the buttons in telegram'''
        query = update.callback_query
        user_id = update.effective_chat.id
        # CallbackQueries need to be answered, even if no notification to the
        # user is needed
        # Some clients may have trouble otherwise. See https://
        # core.telegram.org/bots/api#callbackquery
        query.answer()

        command = query.data.split("_")
        if(command[0] == "subscribe"):
            result = execute_query(self.sqlite_connection,
                                   db_const.LOOKUP_USER.format(user_id))
            if len(result) == 0:
                username = update.callback_query.message.chat.username
                execute_query(self.sqlite_connection,
                              db_const.INSERT_USER.format(user_id, username))

            database_query = db_const.SUB_USER_REGION_LOOKUP.format(user_id,
                                                                    command[1])

            result = execute_query(self.sqlite_connection,
                                   database_query)

            # CHeck if the susbcribtion is already registered
            if len(result) == 0:
                insert_query = db_const.SUB_USER_REGION_INSERT
                result = execute_query(self.sqlite_connection,
                                       insert_query.format(user_id, command[1]))
                query.edit_message_text(text=tele_const.REGISTERED)
            else:
                query.edit_message_text(text=tele_const.ALREADY_REGISTERED)

        if(command[0] == "unsubscribe"):
            delete_quary = db_const.UBSUB_USER_REGION.format(command[1],
                                                             user_id)
            result = execute_query(self.sqlite_connection,
                                   delete_quary)

            reply = tele_const.USER_UNSUBSCRIPTION.format(command[2])
            query.edit_message_text(text=reply)

    def start(self, update, context):
        '''
        Starts the messaging with the user and tells him about the bot and
        the available commands
        '''

        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=tele_const.START_MESSAGE,
                                 parse_mode=telegram.ParseMode.HTML)

        userid = update.effective_chat.id
        print(userid)
        print(update.message.chat.username)

    def under_construction(self, update, context):
        '''
        Send a Message to the user, that the command is currently under
        construction
        '''
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=tele_const.CMD_NOT_AVAILABLE)

    def subscribe_to_region(self, update, context):
        '''
        Lets the user subscribe to a region
        '''
        if len(context.args) != 1:
            reply = tele_const.INV_ARG_CNT.format(tele_const.CMD_SUB,
                                                  tele_const.CMD_SUB_ARG)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=reply)
        else:
            query = db_const.SEARCH_REGIONS.format(context.args[0])
            result = execute_query(self.sqlite_connection, query)

            # If the result-touple is empty, than there are not regions
            # called the way the suer put it in
            if(len(result) == 0):
                response = tele_const.NO_REGION_FOUND.format(context.args[0])
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=response)
                return
            # If there are more results, we have to let the sure to let the
            # user know about that
            if(len(result) >= 1):

                region_keyboard = []

                for item in result:
                    command = "{0}_{1}".format(tele_const.CMD_SUB_PREFIX,
                                               str(item[1]))
                    button = InlineKeyboardButton(text=str(item[0]),
                                                  callback_data=command)
                    region_keyboard.append([button])

                reply_markup = InlineKeyboardMarkup(region_keyboard,
                                                    one_time_keyboard=True)

                response = tele_const.MULTIPLE_REGIONS
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=response,
                                         reply_markup=reply_markup)

                return

    def unsubscribe_from_regions(self, update, context):
        '''Lets the user unsubscribe from regions'''

        # Check if the user supplied more than one argument
        if len(context.args) > 1:
            reply = tele_const.INV_ARG_CNT.format(tele_const.CMD_UNSUB,
                                                  tele_const.CMD_UNSUB_ARG)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=reply)
            return
        if len(context.args) == 1:
            if(context.args[0] == "all"):
                # TODO:insubscribe from all regions ...
                pass
            return

        regions_query = db_const.REGIONS_QUERY.format(update.effective_chat.id)
        result = execute_query(self.sqlite_connection, regions_query)

        if(len(result) > 0):
            region_keyboard = []

            for item in result:
                command = "{0}_{1}_{2}".format(tele_const.CMD_UNSUB_PREFIX,
                                               str(item[0]),
                                               str(item[1]))
                button = InlineKeyboardButton(text=str(item[1]),
                                              callback_data=command)
                region_keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(region_keyboard,
                                                one_time_keyboard=True)
            response = tele_const.REGISTERED_REGIONS
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=response,
                                     reply_markup=reply_markup)
        if(len(result) == 0):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)

    def list_all_regions(self, update, context):
        '''Lists all the regions the user has subscribed to'''
        regions_query = db_const.REGIONS_QUERY.format(update.effective_chat.id)
        result = execute_query(self.sqlite_connection, regions_query)
        if(len(result) > 0):
            # mehr als eine Region
            response = tele_const.USER_SUBSCRIPTIONS

            for item in result:
                response += f"* {item[1]}\n"

            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=response)
        if(len(result) == 0):
            # keine region
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''
    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(filename='corona_bot.log',
                        filemode='w',
                        format='%(name)s - %(levelname)s - %(message)s')
    TelegramBot()


if __name__ == "__main__":
    main()
