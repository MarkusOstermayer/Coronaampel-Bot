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
from telegram.ext import Updater
from telegram.ext import CommandHandler

from constants import TelegramConstants as tele_const


class TelegramBot():
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
                                              self.under_construction))
        dispatcher.add_handler(CommandHandler('showsubscriptions',
                                              self.under_construction))

        # connect to the database
        sqlite_connection = sqlite3.connect("corona_bot_database.db",
                                            check_same_thread=False)
        self.cursor = sqlite_connection.cursor()

        updater.start_polling()

        #  Block until the you presses Ctrl-C or the process receives SIGINT,
        #  SIGTERM or SIGABRT. This should be used most of the time, since
        #  start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()

    def start(self, update, context):
        '''
        Starts the messaging with the user and tells him about the bot and
        the available commands
        '''
        print(update['message']['text'])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=tele_const.START_MESSAGE,
                                 parse_mode=telegram.ParseMode.HTML)
        print(update.message.chat_id)

    def under_construction(self, update, context):
        '''
        Send a Message to the user, that the command is currently under
        construction
        '''
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=tele_const.CMD_NOT_AVAILABLE)

    def subscribe_to_region(self, update, context):
        '''
        Lets the suer subscribe to a region
        '''
        if len(context.args) != 1:
            reply = tele_const.INV_ARG_CNT.format(tele_const.CMD_SUB,
                                                  tele_const.CMD_SUB_ARG)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=reply)
        else:
            name = "%{0}%".format(context.args[0])
            quarry = "select name, type from regions where name like ?"

            cursor = self.sqlite_connection.cursor()
            cursor.execute(quarry, (name,))
            result = cursor.fetchall()

            response = tele_const.MULTIPLE_REGIONS
            for item in result:
                response = response + f"{item[0]}" + "\n"

            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=response)


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''
    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(filename='corona_bot.log',
                        filemode='w',
                        format='%(name)s - %(levelname)s - %(message)s')
    TelegramBot()


if __name__ == "__main__":
    main()
