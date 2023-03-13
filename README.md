# Winter-Dragon-Bot

## Description

This is a personal project to learn and improve at python.

Coding has helped me improve lots, and thus i have rewritten some functionality over time

causing a more robust, error-free and secure project!

## How to install:

This project uses lots of modules that need to be downloaded, these can be installed using

 `pip install -r .\requirements.txt`

To use MongoDB make sure in config.py the following settings are applied

* in class Main:
  `use_database:bool = True`
  `database_name:str = "YourDatabaseName"`
* in class Database:
  `IP_PORT:str = "localhost:27017"`
  `USER_PASS:str = "User:Password"`
  `AUTH_METHOD:str = "SCRAM-SHA-256"`

If you dont use MongoDB, you can use files by changing config.py to match the following:

* In class main:
  ``USE_DATABASE:bool = True``

## Features:

The use of MongoDB as a database solution,

A option for when MongoDB isn't used

Lots of slash commands with lots of features

customizability using a config file

2 seperate log files for the bot and discord.

Lots of error handling

And more!
