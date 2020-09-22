#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A telegram-bot to inform about updates of the austrian corona-ampel
"""


from datetime import datetime
import json
import logging
import sqlite3
import threading
import time


from apscheduler.schedulers.background import BackgroundScheduler
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater


import constants as const
from constants import Database as db_const
from constants import Logging as logg_const
from constants import TelegramConstants as tele_const
import data_builder
import utils
from utils import execute_query, get_data_js


def get_username(chat):
    items = [chat.first_name, chat.last_name]
    username = ""
    for item in items:
        if item is not None:
            username += str(item)

    return username
class TelegramBot(threading.Thread):
    '''Class for the telegram-bot'''

    def __init__(self, token, sql_path):
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
        self.dispatcher.add_handler(CommandHandler('help', self.cmd_help))
        self.dispatcher.add_handler(CommandHandler('caseinfo',
                                                   self.cmd_caseinfo))
        self.dispatcher.add_handler(CommandHandler('start', self.cmd_help))
        self.dispatcher.add_handler(CommandHandler('showsubscriptions',
                                                   self.cmd_list_regions))
        self.dispatcher.add_handler(CommandHandler('sources',
                                                   self.cmd_sources))
        self.dispatcher.add_handler(CommandHandler('subscribe',
                                                   self.cmd_subscribe))
        self.dispatcher.add_handler(CommandHandler(
            'unsubscribe',
            self.cmd_unsubscribe))
        self.dispatcher.add_handler(MessageHandler(Filters.command,
                                                   self.cmd_unknown_command))

        # Adding a Callback-handler for handling subscriptions and other
        # inline-keyboard elements
        self.dispatcher.add_handler(CallbackQueryHandler(self.command_handler))
        logging.info(logg_const.REGISTERED_HANDLER)

        # start a background scheduler for pulling updates from the database
        self.scheduler = BackgroundScheduler()

        # Run the job every day at 8 am
        # this job checks for updates in the database and sends messages to
        # the users
        self.scheduler.add_job(self.pull_updates, 'cron', hour="8", minute="0")
        # this job clears the cached information from the covid dashbaord
        # this will be cleared every hour.
        self.scheduler.add_job(get_data_js.cache_clear, 'cron',
                               minute="0", second="0")
        self.scheduler.start()

        # connect to the database
        self.sqlite_connection = sqlite3.connect(sql_path,
                                                 check_same_thread=False)

    def cmd_caseinfo(self, update, context):
        '''Used to inform about the current pandemic'''

        # Get some variables of the chat message and the user for later use and
        # logging

        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))
        result_data = {}

        # get the information from the dashboard
        for url in const.EPIDEMIC_OVERVIEW_URLS:
            request_result = get_data_js(const.DASHBOARD_URL_PREFIX + url)
            result_data = dict(result_data, **request_result)

        # store it in variables for later use
        total_tests = result_data["dpGesTestungen"]
        pos_tests_total = int(
            result_data["dpPositivGetestet"].replace(
                ".", ""))
        confirmed_cases_quarantine = int(
            result_data["dpBFNH"].replace(".", ""))
        pos_tests_crr = int(
            result_data["dpAktuelleErkrankungen"].replace(
                ".", ""))
        persons_hospital = pos_tests_crr - confirmed_cases_quarantine

        avail_int_care = int(result_data["dpGesIBVerf"].replace(".", ""))

        int_care_curr_use = int(result_data["dpGesIBBel"].replace(".", ""))
        int_care_percent = result_data["dpAktuelleErkrankungen"]
        avail_care = int(result_data["dpGesNBVerf"].replace(".", ""))
        care_curr_use = int(result_data["dpGesNBBel"].replace(".", ""))
        female = result_data["dpGeschlechtsverteilung"][0]["y"]
        male = result_data["dpGeschlechtsverteilung"][1]["y"]
        update_time = result_data["GesamtzahlTestungenVersion"].split("V")[0]
        tests_perc = (100 / (pos_tests_total / pos_tests_crr))

        int_care_percent = (100 / (avail_int_care / int_care_curr_use))
        care_percent = (100 / (avail_care / care_curr_use))

        # format the string accordingly
        caseinfo = tele_const.EPIDEMIC_OVERVIEW.format(
            tests_total=total_tests,
            pos_tests_total=pos_tests_total,
            pos_tests_curr=pos_tests_crr,
            tests_perc=tests_perc,
            hospital=persons_hospital,
            avail_int_care=avail_int_care,
            int_care_curr_use=int_care_curr_use,
            int_care_percent=int_care_percent,
            avail_care=avail_care,
            care_percent=care_percent,
            care_curr_use=care_curr_use,
            female=female,
            male=male,
            update_time=update_time
        )

        # send the message to the user
        context.bot.send_message(chat_id=user_id,
                                 text=caseinfo,
                                 parse_mode=telegram.ParseMode.HTML)

    def cmd_help(self, update, context):
        '''
        Starts the messaging with the user and tells him about the bot and
        the available commands
        '''

        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.START_MESSAGE,
                                 parse_mode=telegram.ParseMode.HTML)

    def cmd_list_regions(self, update, context):
        '''Lists all the regions the user has subscribed to'''

        user_name = get_username(update.message.chat)
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
                warn_quarry = db_const.CHECK_WARNING.format(region_id=item[1])
                warn_result = execute_query(
                    self.sqlite_connection, warn_quarry)

                response += tele_const.LIST_REGION.format(
                    alert_level=const.ALERT_COLORS[warn_result[0][3]],
                    region_name=item[0])

            context.bot.send_message(chat_id=user_id,
                                     text=response)
        if(len(result) == 0):
            # keine region
            context.bot.send_message(chat_id=user_id,
                                     text=tele_const.NO_SUBSCRIPTIONS_FOUND)

    def cmd_sources(self, update, context):
        '''Inform the user about the used data-sources'''
        # Get some variables of the chat message and the user for later use and
        # logging
        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.SOURCES_URLS,
                                 disable_web_page_preview=True,
                                 parse_mode=telegram.ParseMode.HTML)

    def cmd_subscribe(self, update, context):
        '''
        Lets the user subscribe to a region
        '''
        # Get some variables of the chat message and the user for later use and
        # logging

        user_name = get_username(update.message.chat)
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

        regions_query = db_const.SEARCH_REGIONS.format(region_name=region_name)

        cmd_button_list = utils.region_cmd_buttons(
            self.sqlite_connection, regions_query, tele_const.CMD_SUB_PREFIX)

        if cmd_button_list is None:
            region_not_found = tele_const.NO_REGION_FOUND.format(
                region_name=region_name)

            context.bot.send_message(chat_id=user_id, text=region_not_found)
        else:
            reply_markup = InlineKeyboardMarkup(cmd_button_list,
                                                one_time_keyboard=True)
            response = tele_const.MULTIPLE_REGIONS
            context.bot.send_message(chat_id=user_id,
                                     text=response,
                                     reply_markup=reply_markup)

    def cmd_under_construction(self, update, context):
        '''
        Send a Message to the user, that the command is currently under
        construction
        '''

        # Safe some variables and log the message the user send
        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id

        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        # Send the user a message, telling him that this command is currently
        # not available
        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.CMD_NOT_AVAILABLE)

    def cmd_unknown_command(self, update, context):
        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        context.bot.send_message(chat_id=user_id,
                                 text=tele_const.UNKNOWN_COMMAND)

    def cmd_unsubscribe(self, update, context):
        '''Lets the user unsubscribe from regions'''

        user_name = get_username(update.message.chat)
        message = update.message.text
        user_id = update.effective_chat.id
        logging.info(logg_const.USER_SEND_MSG.format(username=user_name,
                                                     msg=message))

        # Check if the user supplied more than one argument
        if len(context.args) > 1:
            reply = tele_const.INV_ARG_CNT.format(
                cmd=tele_const.CMD_UNSUB, args=tele_const.CMD_UNSUB_ARG)
            context.bot.send_message(chat_id=user_id,
                                     text=reply)
            return
        # Check if the user wants to unsubscribe from all regions
        elif len(context.args) == 1:
            if(context.args[0] == "all"):
                unsub_all_quarry = db_const.UBSUB_USER_ALL_REGION.format(
                    user_id=user_id)
                execute_query(self.sqlite_connection, unsub_all_quarry)

                context.bot.send_message(chat_id=user_id,
                                         text=tele_const.USER_UNSUBSCRIBE_ALL)
                return
            else:
                reply = tele_const.INV_ARG_CNT.format(
                    cmd=tele_const.CMD_UNSUB, args=tele_const.CMD_UNSUB_ARG)
                context.bot.send_message(chat_id=user_id,
                                         text=reply)
                return

        # If there are no arguments, than the user has to choose
        else:
            regions_query = db_const.REGIONS_QUERY.format(user_id=user_id)

            cmd_button_list = utils.region_cmd_buttons(
                self.sqlite_connection, regions_query,
                tele_const.CMD_UNSUB_PREFIX)

            if cmd_button_list is None:
                context.bot.send_message(
                    chat_id=user_id, text=tele_const.NO_SUBSCRIPTIONS_FOUND)
            else:
                reply_markup = InlineKeyboardMarkup(cmd_button_list,
                                                    one_time_keyboard=True)
                response = tele_const.REGISTERED_REGIONS
                context.bot.send_message(chat_id=user_id,
                                         text=response,
                                         reply_markup=reply_markup)

    def command_handler(self, update, context):
        '''Used to handle commands, send by the buttons in telegram'''
        # get some basic information's about the message for logging and later
        # use
        query = update.callback_query
        user_id = update.effective_chat.id
        username = get_username(update.callback_query.message.chat)
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
            # if the length of the result is 0, than the user is not in
            # the database and has to be registered
            if len(result) == 0:
                # Execute the insert-quarry, replacing the placeholders with
                # the users id and username
                execute_query(self.sqlite_connection,
                              db_const.INSERT_USER.format(id=user_id,
                                                          name=username))

                logging.info(logg_const.REGISTERED_USER.format(name=username,
                                                               id=user_id))
            # get the id of the region for the quarry
            reg_id = command[1]
            lookup_reg = db_const.SUB_USER_REGION_LOOKUP.format(
                user_id=user_id, region_id=reg_id)

            # execute the quary
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

        # check if the command is a unsusbcribe_command
        elif(command[0] == tele_const.CMD_UNSUB_PREFIX):
            # if it is the unsusbcribe-command, issue an quarry and delete the
            # entry in the database (subscription)
            del_query = db_const.UBSUB_USER_REGION.format(region_id=command[1],
                                                          user_id=user_id)

            result = execute_query(self.sqlite_connection, del_query)

            # get the name of the region the user unsubscribed from
            reg_name = command[2]

            # tell him about the unsusbcription and log the event
            reply = tele_const.USER_UNSUBSCRIPTION.format(region_name=reg_name)
            query.edit_message_text(text=reply)
            logging.info(logg_const.USER_UNSUB.format(user_name=username,
                                                      region_name=command[2]))
        # check if the command is just the cancel-operation command
        elif(command[0] == tele_const.CMD_PREFIX_CANCEL):
            query.edit_message_text(text=tele_const.CANCEL_OPERATION)

        return None

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


def main():
    '''The main programmfunction, gats calles whenever the modul is run'''

    log_filename = const.TELEGRAM_BOT_LOG.format(
        date=datetime.date(datetime.now()))

    logging.basicConfig(format='%(asctime)s:%(levelname)s - %(message)s',
                        level=logging.INFO,
                        handlers=[logging.FileHandler(log_filename),
                                  logging.StreamHandler()])

    with open(const.CONFIG_FILE, "r") as file:
        configurations = json.loads(file.read())

    # initialize the bot
    telegram_bot = TelegramBot(configurations["telegram-token"],
                               configurations["database_path"])
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
