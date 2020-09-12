#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A constantsfile for the project
"""


CORONAKOMMISSIONV2 = ("https://corona-ampel.gv.at"
                      "/sites/corona-ampel.gv.at/files/coronadata/"
                      "CoronaKommissionV2.json")

CONFIG_FILE = "config.json"

DATABASE_FILE = "corona_db.sqlite"

DATA_BUILDER_LOG = "corona_data_builder.log"

ALERT_URL = {
            1: "https://corona-ampel.gv.at/ampelfarben/geringes-risiko-gruen/",
            2: "https://corona-ampel.gv.at/ampelfarben/mittleres-risiko-gelb/",
            3: "https://corona-ampel.gv.at/ampelfarben/hohes-risiko-orange/",
            4: "https://corona-ampel.gv.at/ampelfarben/sehr-hohes-risiko-rot/"
}

ALERT_COLORS = {
                1: "🟢",
                2: "🟡",
                3: "🟠",
                4: "🔴"}


class Logging():
    '''Used tor logging some events'''

    CREATING_DATABASE = "Creating database ..."
    DATABASE_CREATED = "Database created!"

    CREATING_TABLES = "Creating tables ..."
    TABLES_CREATED = "Tables created!"

    INSERT_SUCCESS = "Inserted {region_name} into the region-table"

    REGISTERED_USER = "Registered new user {name}(ID: {id})"

    USER_SUB = "User {user_name} just subscribed to {region_name}"

    USER_UNSUB = "User {user_name} just unsubscribed from {region_name}"

    STARTING_BOT = "Setup bot ..."
    STARTED_BOT = "Setup completed, starting polling"

    REGISTER_HANDLER = "registrating handler ..."
    REGISTERED_HANDLER = "handler registered!"

    USER_SEND_MSG = "User {username} send the following message: {msg}"

    USER_UPDATE = "Inform {username} about the update in region {region_name}"


class Database():
    '''Used for inserting and Loggging database events'''
    QUERY_EXECUTED = "Quarry [{quary}] successfull executes"

    EXCEPTION_MSG = ("An {exc_name} occured while executing the Quarry "
                     "[{quary}] ")

    DB_ERROR = "database error"

    OP_ERROR = "operational error"

    REGION_CHECK = ("SELECT * FROM regions WHERE (id={id} AND type='{type}' "
                    "AND name='{name}');")

    INSERT_REGION = ("INSERT INTO regions "
                     "(id, type, name) "
                     "VALUES ({id}, '{type}', '{name}');")

    CHECK_WARNING = ("SELECT revision, kw, regions_id, alert_level, reason "
                     "FROM warnings "
                     "WHERE (regions_id={region_id}) "
                     "ORDER BY revision DESC;")

    INSERT_WARNING = ("INSERT INTO warnings "
                      "(revision, kw, regions_id, alert_level, reason) "
                      "VALUES ({revision}, {kw}, {region_id}, {alert_level}, "
                      "'{reason}');")
    ADD_UPDATE = ("INSERT INTO updates "
                  "(region_id, telegram) VALUES "
                  "({region_id}, 0);")

    REGIONS_QUERY = ("select regions.id, regions.name "
                     "from users, regions, subscriptions "
                     "where (subscriptions.regions_id = regions.id "
                     "and subscriptions.users_id = {user_id} "
                     "and subscriptions.users_id = users.id);")

    SEARCH_REGIONS = ("select name, id from regions where name like "
                      "'%{region_name}%' "
                      "and type = 'Gemeinde';")

    LOOKUP_USER = "select id from users where users.id = {user_id};"

    INSERT_USER = ("insert into users "
                   "(id, name) values "
                   "({id}, '{name}');")

    SUB_USER_REGION_LOOKUP = ("select id from subscriptions "
                              "where users_id = {user_id} "
                              "and regions_id = {region_id}")

    SUB_USER_REGION_INSERT = ("insert into subscriptions "
                              "(users_id, regions_id) values "
                              "({user_id}, {region_id});")
    UBSUB_USER_REGION = ("DELETE FROM subscriptions "
                         "WHERE (subscriptions.regions_id = {region_id} "
                         "and subscriptions.users_id = {user_id});")

    CREATE_REGIONS_TABLE = ("CREATE TABLE IF NOT EXISTS regions ("
                            "id INTEGER PRIMARY KEY, "
                            "type TEXT, "
                            "name TEXT);")

    CREATE_WARNINGS_TABLE = ("CREATE TABLE IF NOT EXISTS warnings ("
                             "revision INTEGER, "
                             "kw INTEGER, "
                             "regions_id TEXT, "
                             "alert_level INTEGER, "
                             "reason TEXT, "
                             "PRIMARY KEY(revision,kw, regions_id), "
                             "FOREIGN KEY(regions_id) REFERENCES regions(id));"
                             )

    CREATE_USERS_TABLE = ("CREATE TABLE IF NOT EXISTS users ( "
                          "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                          "name TEXT);")

    CREATE_SUBSCRIPTIONS_TABLE = ("CREATE TABLE IF NOT EXISTS subscriptions ( "
                                  "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                                  "users_id INTEGER, "
                                  "regions_id  INTEGER, "
                                  "FOREIGN KEY(users_id) REFERENCES users(id) "
                                  "FOREIGN KEY(regions_id) "
                                  "REFERENCES "
                                  "regions(id));")

    CREATE_UPDATES_TABLE = ("CREATE TABLE IF NOT EXISTS updates ("
                            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                            "region_id INTEGER, "
                            "telegram INTEGER);")
    GET_UPDATED_REGIONS = "select region_id from updates where telegram = 0;"

    GET_REGIONUPDATES = ("select regions.name, warnings.alert_level from "
                         "warnings , regions "
                         "where (warnings.regions_id = {id} and "
                         "warnings.regions_id = regions.id) "
                         "order by warnings.revision DESC "
                         "Limit 2;")
    '''
    LOOKUP_REGION_SUBSCRIPTIONS = ("select subscriptions.users_id from "
                                   " subscriptions where "
                                   "subscriptions.regions_id = {region_id}")
    '''

    LOOKUP_REGION_SUBSCRIPTIONS = ("select subscriptions.users_id, "
                                   "users.name  from subscriptions, users "
                                   "where "
                                   "subscriptions.regions_id = {region_id} "
                                   "and subscriptions.users_id = users.id;")

    MARK_UPDATE_AS_READ = ("UPDATE updates "
                           "set telegram = 1 "
                           "where region_id = {region_id};")


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
                   "Please note, that the command {cmd} uses "
                   "{args} as argument 🙂")

    MULTIPLE_REGIONS = ("Hmmm, I found the following regions🤔\n"
                        "Just let me know what region you mean 😄\n")
    NO_REGION_FOUND = ("Hmmm, I found no region called {region_name}🤔\n"
                       "Make sure you typed it correct 😄")
    ALREADY_REGISTERED = ("Hmmm, it looks like you have already registered for"
                          " this region🤔\n")

    REGISTERED = "Okey, I have just registered you for {region_name} 😄"

    REGISTERED_REGIONS = "Okey, I found the following registrations 😄"

    NO_SUBSCRIPTIONS_FOUND = ("It looks like, that you do not have any "
                              "subscriptions jet😄")

    USER_SUBSCRIPTIONS = "You subscribe for the following regions: \n"

    LIST_REGION = "🔘 {region_name}\n"

    USER_UNSUBSCRIPTION = "You just unsubscribed from {region_name}"

    REGION_LOWER_ALERT = ("🟢 Good News! \n\n")

    REGION_HIGHER_ALERT = ("🔴 Bad News! \n\n")

    REGION_ALERT_BODY = ("{city_name} just went from alertlevel "
                         "{level1} to {level2}\n"
                         "This means, the following restrictions apply for "
                         "this area:\n{url_link}")
