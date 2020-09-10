#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A telegram-bot to inform about updates of the corona-ampel
"""


import json
import logging
import sqlite3

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler

import constants as const
from constants import TelegramConstants as tele_const
from constants import Database as db_const
from constants import Logging as logg_const


def execute_query(connection, query):
    '''Execute Quarrys on the dabasase'''

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


class TelegramBot():
    '''Class for the telegram-bot'''
    def __init__(self):
        '''Initiate the bot, register all the handlers and start polling'''
        logging.info(logg_const.STARTING_BOT)

        with open(const.CONFIG_FILE, "r") as file:
            result = json.loads(file.read())
        updater = Updater(token=result["telegram-token"], use_context=True)
        dispatcher = updater.dispatcher

        logging.info(logg_const.REGISTER_HANDLER)

        # Telegram-Commandhandler
        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('subscribe',
                                              self.subscribe_to_region))
        dispatcher.add_handler(CommandHandler('unsubscribe',
                                              self.unsubscribe_from_regions))
        dispatcher.add_handler(CommandHandler('showsubscriptions',
                                              self.list_all_regions))

        # Adding a Callback-handler for handling subscriptions and other
        # inline-keybord elements
        dispatcher.add_handler(CallbackQueryHandler(self.command_handler))
        logging.info(logg_const.REGISTERED_HANDLER)

        # connect to the database
        self.sqlite_connection = sqlite3.connect("corona_db.sqlite",
                                                 check_same_thread=False)

        # start pooling
        logging.info(logg_const.STARTED_BOT)
        updater.start_polling()

        #  Block until the you presses Ctrl-C or the process receives SIGINT,
        #  SIGTERM or SIGABRT. This should be used most of the time, since
        #  start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()

    def command_handler(self, update, context):
        '''Used to handle commandas, send by the buttons in telegram'''
        # get some basic informations about the message for logging and later
        # use
        query = update.callback_query
        user_id = update.effective_chat.id
        username = update.callback_query.message.chat.username

        # CallbackQueries need to be answered, even if no notification to the
        # user is needed
        # Some clients may have trouble otherwise. See https://
        # core.telegram.org/bots/api#callbackquery
        # ref: https://github.com/python-telegram-bot/python-telegram-bot/blob/
        # master/examples/inlinekeyboard.py
        query.answer()

        command = query.data.split("_")

        # If the issued command is a subscription, than this block needs to be
        # run
        if(command[0] == tele_const.CMD_SUB_PREFIX):

            # bevor we register the user, wen need to check if he is already in
            # our userdatabase, it not, he weill be inserted into it on his
            # first subscription
            result = execute_query(self.sqlite_connection,
                                   db_const.LOOKUP_USER.format(user_id=user_id)
                                   )
            # if the length of the result is 0, than the user yould not be
            # found in the database and therefor isn't in it jet
            if len(result) == 0:
                # Execute the insert-quary, replacing the palceholders with the
                # users id and username
                execute_query(self.sqlite_connection,
                              db_const.INSERT_USER.format(id=user_id,
                                                          name=username))

                logging.info(logg_const.REGISTERED_USER.format(name=username,
                                                               id=user_id))

            reg_id = command[1]
            lookup_reg = db_const.SUB_USER_REGION_LOOKUP.format(user_id=user_id,
                                                                region_id=reg_id
                                                                )

            result = execute_query(self.sqlite_connection, lookup_reg)

            # Check if the susbcribtion is already registered
            if len(result) == 0:
                # it not, than insert the usersubscription into the database
                insert_query = db_const.SUB_USER_REGION_INSERT
                result = execute_query(self.sqlite_connection,
                                       insert_query.format(user_id=user_id,
                                                           region_id=command[1])
                                       )

                # and tell him about the registration
                response = tele_const.REGISTERED.format(region_name=command[2])
                query.edit_message_text(text=response)

                logging.info(logg_const.USER_SUB.format(user_name=username,
                                                        region_name=command[2]))
            else:
                query.edit_message_text(text=tele_const.ALREADY_REGISTERED)

        if(command[0] == tele_const.CMD_UNSUB_PREFIX):

            del_query = db_const.UBSUB_USER_REGION.format(region_id=command[1],
                                                          user_id=user_id)
            result = execute_query(self.sqlite_connection, del_query)

            reg_name = command[2]
            reply = tele_const.USER_UNSUBSCRIPTION.format(region_name=reg_name)
            query.edit_message_text(text=reply)
            logging.info(logg_const.USER_UNSUB.format(user_name=username,
                                                      region_name=command[2]))

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

    def subscribe_to_region(self, update, context):
        '''
        Lets the user subscribe to a region
        '''
        if len(context.args) != 1:
            reply = tele_const.INV_ARG_CNT.format(cmd=tele_const.CMD_SUB,
                                                  args=tele_const.CMD_SUB_ARG)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=reply)
            return

        region_name = context.args[0]

        query = db_const.SEARCH_REGIONS.format(region_name=region_name)
        result = execute_query(self.sqlite_connection, query)

        # If the result-touple is empty, than there are not regions
        # called the way the suer put it in
        if(len(result) == 0):

            respons = tele_const.NO_REGION_FOUND.format(region_name=region_name)

            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=respons)
            return
        # If there are more results, we have to let the sure to let the
        # user know about that
        if(len(result) >= 1):
            region_keyboard = []

            for item in result:
                command = "{0}_{1}_{2}".format(tele_const.CMD_SUB_PREFIX,
                                               str(item[1]),
                                               str(item[0]))
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

    def under_construction(self, update, context):
        '''
        Send a Message to the user, that the command is currently under
        construction
        '''
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=tele_const.CMD_NOT_AVAILABLE)

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

        user_id = update.effective_chat.id
        regions_query = db_const.REGIONS_QUERY.format(user_id=user_id)
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
            response = tele_const.REGISTERED_REGIONS.format
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=response,
                                     reply_markup=reply_markup)
        if(len(result) == 0):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)

    def list_all_regions(self, update, context):
        '''Lists all the regions the user has subscribed to'''
        user_id = update.effective_chat.id
        regions_query = db_const.REGIONS_QUERY.format(user_id=user_id)
        result = execute_query(self.sqlite_connection, regions_query)
        if(len(result) > 0):
            # mehr als eine Region
            response = tele_const.USER_SUBSCRIPTIONS

            for item in result:
                response += f"* {item[1]}\n"

            context.bot.send_message(chat_id=user_id,
                                     text=response)
        if(len(result) == 0):
            # keine region
            context.bot.send_message(chat_id=user_id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''

    logging.basicConfig(format='%(asctime)s:%(levelname)s - %(message)s',
                        level=logging.INFO,
                        handlers=[logging.FileHandler("corona_bot.log"),
                                  logging.StreamHandler()])

    TelegramBot()


if __name__ == "__main__":
    main()
