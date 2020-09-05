# !/usr/bin/python3
#  -*- coding: utf-8 -*-

"""
A constantsfile for the project
"""

__copyright__ = "Copyright 2020"

CORONAKOMMISSIONV2 = ("https://corona-ampel.gv.at"
                      "/sites/corona-ampel.gv.at/files/coronadata/"
                      "CoronaKommissionV2.json")


class Logging():
    '''Used tor logging some events'''
    INSERT_SUCCESS = "Inserted {0} into the region-table"


class DATABASE():
    '''Used for inserting and Loggging database events'''
    QUERY_EXECUTED = "Quarry {0} successfull executes"

    EXCEPTION_MSG = "An {0} occured while executing the Quarry {1}"

    DB_ERROR = "database error"

    OP_ERROR = "operational error"

    REGION_CHECK = "SELECT * FROM regions WHERE (id=? AND type=? AND name=?)"

    INSERT_REGION = ("INSERT INTO regions "
                     "(id, type, name) "
                     "VALUES {0}")

    CHECK_WARNING = ("SELECT revision, kw, regions_id, alert_level, reason "
                     "FROM warnings "
                     "WHERE (regions_id=?) "
                     "ORDER BY revision DESC")

    INSERT_WARNING = ("INSERT INTO warnings "
                      "(revision, kw, regions_id, alert_level, reason) "
                      "VALUES {0}")
    ADD_UPDATE = ("INSERT INTO updates "
                  "(region_id) VALUES "
                  "({0})")

    REGIONS_QUERY = ("select regions.id, regions.name "
                     "from users, regions, subscriptions "
                     "where (subscriptions.regions_id = regions.id "
                     "and subscriptions.users_id = {0});")
    SEARCH_REGIONS = ("select name, id from regions where name like '%{0}%' "
                      "and type = 'Gemeinde'")

    LOOKUP_USER = "select id from users where users.id = {0};"

    INSERT_USER = ("insert into users "
                   "(id, name) values "
                   "({0}, '{1}')")

    SUB_USER_REGION_LOOKUP = ("select id from subscriptions "
                              "where users_id = {0} "
                              "and regions_id = {1}")

    SUB_USER_REGION_INSERT = ("insert into subscriptions "
                              "(users_id, regions_id) values "
                              "({0}, {1});")
    UBSUB_USER_REGION = ("DELETE FROM subscriptions "
                         "WHERE (subscriptions.regions_id = {0} "
                         "and subscriptions.users_id = {1});")
# -----------------------------------------------------------------------------
#                                                    SQLite
# ----------------------------------------------------------------------------
CREATE_REGIONS_TABLE = """
CREATE TABLE IF NOT EXISTS regions (
  id INTEGER PRIMARY KEY,
  type TEXT,
  name TEXT
);
"""

CREATE_WARNINGS_TABLE = """
CREATE TABLE IF NOT EXISTS warnings (
  revision INTEGER,
  kw INTEGER,
  regions_id TEXT,
  alert_level INTEGER,
  reason TEXT,
  PRIMARY KEY(revision,kw, regions_id),
  FOREIGN KEY(regions_id) REFERENCES regions(id)
);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT
);
"""

CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  users_id INTEGER,
  regions_id  INTEGER,
  FOREIGN KEY(users_id) REFERENCES users(id) FOREIGN KEY(regions_id) REFERENCES
  regions(id)
);
"""

CREATE_UPDATES_TABLE = """
CREATE TABLE IF NOT EXISTS updates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  region_id INTEGER
);
"""


class TelegramConstants():
    '''A class for storing telegram-constant values'''
    CMD_SUB = "/subscribe"
    CMD_UNSUB = "//unsubscribe "

    CMD_SUB_ARG = "a city or region"
    CMD_UNSUB_ARG = "<all>"

    CMD_UNSUB_PREFIX = "unsubscribe"
    CMD_SUB_PREFIX = "subscribe"


    START_MESSAGE = ("Hi 👋, this are the commands I know.\n"
                     "\n"
                     "<b>Subscribing and Unsubscribing</b>\n"
                     "/subscribe [Cityname] - "
                     "Used to register for an alert for a city\n"
                     "/unsubscribe or /unsubscribe all - "
                     "Unsubscribe from one city or from all citys\n"
                     "/showsubscriptions - Show all active subscriptions")

    CMD_NOT_AVAILABLE = ("⚠️ Not available ⚠️\n"
                         "Oh no, it looks like the command is currently under"
                         "construction 😔\n"
                         "But it will be available 🔜")

    INV_ARG_CNT = ("I have problems understanding you🤔\n"
                   "Please note, that the command {0} uses {1} as argument 🙂")

    MULTIPLE_REGIONS = ("Hmmm, I found the following regions🤔\n"
                        "Just let me know what region you mean 😄\n")
    NO_REGION_FOUND = ("Hmmm, I found no region called {0}🤔\n"
                       "Make sure you typed it correct 😄")
    ALREADY_REGISTERED = ("Hmmm, it looks like you have already registered for "
                          "this region🤔\n")
    REGISTERED = "Okey, I have just registered you for this region😄"


    REGISTERED_REGIONS = "Okey, I found the following registrations 😄"

    NO_SUBSCRIPTIONS_FOUND = ("It looks like, that you do not have any "
                              "subscriptions jet😄")
    USER_SUBSCRIPTIONS = "You subscribted for the following regions: \n"

    USER_UNSUBSCRIPTION = "You just unsubscribted from {0}"
