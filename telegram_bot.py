#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A telegram-bot to inform about updates of the austrian corona-ampel
"""


import json
import logging
import sqlite3
import threading
import time


from apscheduler.schedulers.background import BackgroundScheduler
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Updater

import constants as const
from constants import Database as db_const
from constants import Logging as logg_const
from constants import TelegramConstants as tele_const
from utils import execute_query


class TelegramBot(threading.Thread):
    '''Class for the telegram-bot'''

    def __init__(self, token):
        '''Initiate the bot, register all the handlers and start polling'''

        # Initialize all base classes
        super().__init__()

        self.running = False
        logging.info(logg_const.STARTING_BOT)

        # TODO: check if the bot and the dispatcher/updater can be created
        # more easily
        # Get a bot for later use in the update-function
        self.bot = telegram.Bot(token=token)

        # get updater and dispatcher running
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        logging.info(logg_const.REGISTER_HANDLER)

        # Telegram-Command handler
        self.dispatcher.add_handler(CommandHandler('start', self.start_msg))
        self.dispatcher.add_handler(CommandHandler('subscribe',
                                                   self.subscribe_to_region))
        self.dispatcher.add_handler(
            CommandHandler(
                'unsubscribe',
                self.unsubscribe_from_regions))
        self.dispatcher.add_handler(CommandHandler('showsubscriptions',
                                                   self.list_all_regions))

        # Adding a Callback-handler for handling subscriptions and other
        # inline-keyboard elements
        self.dispatcher.add_handler(CallbackQueryHandler(self.command_handler))
        logging.info(logg_const.REGISTERED_HANDLER)

        # start a background scheduler for pulling updates from the database
        self.scheduler = BackgroundScheduler()

        # Run the job every day at 8 am
        self.scheduler.add_job(self.pull_updates, 'cron', hour="8", minute="0")
        self.scheduler.start()

        # connect to the database
        self.sqlite_connection = sqlite3.connect("corona_db.sqlite",
                                                 check_same_thread=False)

    def run(self):
        # TODO: Probably not optimal, because ctrl+c still gets passed th toe
        # dispatcher and updater
        # start pooling
        logging.info(logg_const.STARTED_BOT)
        self.updater.start_polling()
        self.running = True

        #  Block until you presses Ctrl-C.
        while self.running:
            time.sleep(1)

        logging.info("Stopping updater and dispatcher ...")
        self.updater.stop()
        self.dispatcher.stop()
        self.scheduler.shutdown(wait=False)

        logging.info("Stopped bot, closing database connection ...")
        # Close the connection to the database
        self.sqlite_connection.close()
        logging.info("Database connection closed!")

    def pull_updates(self):
        '''Pull updates from the database regarding new alert-levels'''

        # get all regions, that are not already red
        result = execute_query(self.sqlite_connection,
                               db_const.GET_UPDATED_REGIONS)

        for region in result:
            region_id = region[0]

            lookup_quarry = db_const.LOOKUP_REGION_SUBSCRIPTIONS.format(
                region_id=region_id)

            lookup_result = execute_query(self.sqlite_connection,
                                          lookup_quarry)
            print(lookup_result)
            # If the lookup does not yield any subscribed user, skip the
            # further lookup, since there is no user to inform
            if len(lookup_result) == 0:
                # This should be here, so that even unregistered regions get
                # marked as read
                mark_update_as_read = db_const.MARK_UPDATE_AS_READ.format(
                    region_id=region_id)

                execute_query(self.sqlite_connection, mark_update_as_read)
                continue

            update = db_const.GET_REGIONUPDATES.format(id=region_id)

            state_result = execute_query(self.sqlite_connection, update)

            response = None
            region_name = state_result[0][0]
            bevor_color = const.ALERT_COLORS[state_result[1][1]]
            after_color = const.ALERT_COLORS[state_result[0][1]]
            url = const.ALERT_URL[state_result[0][1]]

            response = ""
            # the newer level is higher than the older one, the level has risen
            if state_result[0][1] > state_result[1][1]:
                response = tele_const.REGION_HIGHER_ALERT
            else:
                response = tele_const.REGION_LOWER_ALERT

            response += tele_const.REGION_ALERT_BODY.format(
                city_name=region_name,
                level1=bevor_color,
                level2=after_color,
                url_link=url)

            for user in lookup_result:
                logging.info(
                    logg_const.USER_UPDATE.format(
                        username=user[1],
                        region_name=region_name))

                self.bot.send_message(chat_id=user[0],
                                      text=response)

            # mark region as read
            mark_update_as_read = db_const.MARK_UPDATE_AS_READ.format(
                region_id=region_id)

            execute_query(self.sqlite_connection, mark_update_as_read)

    def command_handler(self, update, context):
        '''Used to handle commands, send by the buttons in telegram'''
        # get some basic information's about the message for logging and later
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
                # Execute the insert-quarry, replacing the placeholders with
                # the users id and username
                execute_query(self.sqlite_connection,
                              db_const.INSERT_USER.format(id=user_id,
                                                          name=username))

                logging.info(logg_const.REGISTERED_USER.format(name=username,
                                                               id=user_id))

            reg_id = command[1]
            lookup_reg = db_const.SUB_USER_REGION_LOOKUP.format(
                user_id=user_id, region_id=reg_id)

            result = execute_query(self.sqlite_connection, lookup_reg)

            # Check if the subscription is already registered
            if len(result) == 0:
                # it not, than insert the user subscription into the database
                insert_query = db_const.SUB_USER_REGION_INSERT
                result = execute_query(
                    self.sqlite_connection, insert_query.format(
                        user_id=user_id, region_id=command[1]))

                # and tell him about the registration
                response = tele_const.REGISTERED.format(region_name=command[2])
                query.edit_message_text(text=response)

                logging.info(
                    logg_const.USER_SUB.format(
                        user_name=username,
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

    def start_msg(self, update, context):
        '''
        Starts the messaging with the user and tells him about the bot and
        the available commands
        '''

        user_name = update.message.chat.username
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.START_MESSAGE,
                                 parse_mode=telegram.ParseMode.HTML)

    def subscribe_to_region(self, update, context):
        '''
        Lets the user subscribe to a region
        '''
        # Get some variables of the chat message and the user for later use and
        # logging

        user_name = update.message.chat.username
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        # check if at least one argument got supplied
        if len(context.args) == 0:
            reply = tele_const.INV_ARG_CNT.format(cmd=tele_const.CMD_SUB,
                                                  args=tele_const.CMD_SUB_ARG)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=reply)
            return

        # Strip any " used in the string to express places consisting of
        # multiple words
        region_name = " ".join(context.args).strip('"')

        query = db_const.SEARCH_REGIONS.format(region_name=region_name)
        result = execute_query(self.sqlite_connection, query)

        # If the result-tuple is empty, than there are not regions
        # called the way the suer put it in
        if(len(result) == 0):

            respons = tele_const.NO_REGION_FOUND.format(
                region_name=region_name)

            context.bot.send_message(chat_id=user_id,
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
            context.bot.send_message(chat_id=user_id,
                                     text=response,
                                     reply_markup=reply_markup)

            return

    def under_construction(self, update, context):
        '''
        Send a Message to the user, that the command is currently under
        construction
        '''

        # Safe some variables and log the message the user send
        user_name = update.message.chat.username
        message = update.message.text
        user_id = update.effective_chat.id

        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        # Send the user a message, telling him that this command is currently
        # not available
        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.CMD_NOT_AVAILABLE)

    def unsubscribe_from_regions(self, update, context):
        '''Lets the user unsubscribe from regions'''

        user_name = update.message.chat.username
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        # Check if the user supplied more than one argument
        if len(context.args) > 1:
            reply = tele_const.INV_ARG_CNT.format(tele_const.CMD_UNSUB,
                                                  tele_const.CMD_UNSUB_ARG)
            context.bot.send_message(chat_id=user_id,
                                     text=reply)
            return
        if len(context.args) == 1:
            if(context.args[0] == "all"):
                unsub_all_quarry = db_const.UBSUB_USER_ALL_REGION.format(
                    user_id=user_id)
                execute_query(self.sqlite_connection, unsub_all_quarry)

                context.bot.send_message(chat_id=user_id,
                                         text=tele_const.USER_UNSUBSCRIBE_ALL)
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
            response = tele_const.REGISTERED_REGIONS
            context.bot.send_message(chat_id=user_id,
                                     text=response,
                                     reply_markup=reply_markup)
        if(len(result) == 0):
            context.bot.send_message(chat_id=user_id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)

    def list_all_regions(self, update, context):
        '''Lists all the regions the user has subscribed to'''

        user_name = update.message.chat.username
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        regions_query = db_const.REGIONS_QUERY.format(user_id=user_id)
        result = execute_query(self.sqlite_connection, regions_query)

        if(len(result) > 0):
            # mehr als eine Region
            response = tele_const.USER_SUBSCRIPTIONS

            for item in result:
                warn_quarry = db_const.CHECK_WARNING.format(region_id=item[0])
                warn_result = execute_query(
                    self.sqlite_connection, warn_quarry)

                response += tele_const.LIST_REGION.format(
                    alert_level=const.ALERT_COLORS[warn_result[0][3]],
                    region_name=item[1])

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

    with open(const.CONFIG_FILE, "r") as file:
        configurations = json.loads(file.read())

    # initialize the bot
    telegram_bot = TelegramBot(configurations["telegram-token"])
    telegram_bot.daemon = True

    # start the bot-thread
    telegram_bot.start()

    # loop to keep the bot running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # stop the bot
        telegram_bot.running = False

        # join it with the main thread
        telegram_bot.join()


if __name__ == "__main__":
    main()
