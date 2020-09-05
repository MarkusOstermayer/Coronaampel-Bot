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
  name TEXT,
  level INTEGER
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
    CMD_SUB_ARG = "a city or region"

    START_MESSAGE = ("Hi 👋, this are the commands I know.\n"
                     "\n"
                     "<b>Subscribing and Unsubscribing</b>\n"
                     "/subscribe [Cityname] - "
                     "Used to register for an alert for a city\n"
                     "/unsubscribe [Cityname] or /unsubscribe - "
                     "Unsubscribe from one city or from all citys\n"
                     "/showsubscriptions - Show all active subscriptions")

    CMD_NOT_AVAILABLE = ("⚠️ Not available ⚠️\n"
                         "Oh no, it looks like the command is currently under"
                         "construction 😔\n"
                         "But it will be available 🔜")

    INV_ARG_CNT = ("I have problems understanding you🤔\n"
                   "Please note, that the command {0} uses {1} as argument 🙂")

    MULTIPLE_REGIONS = ("Hmmm, I found the following regions🤔\n"
                        "Just let me know what region you mean 😄")
