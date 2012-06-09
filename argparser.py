# -*- coding: utf-8 -*-

import sys
from log import logging
import io


COMMANDS = {
    # User
    "user": {
        "help": "Create note",
        "flags": {
            "--full": {"help": "Add tag to note", "value": True, "default": False},
        }
    },

    # Notes
    "create": {
        "help": "Create note",
        "arguments": {
            "--title": {"help": "Set note title", "required": True},
            "--body": {"help": "Set note content", "required": True},
            "--tags": {"help": "Add tag to note"},
            "--notepad": {"help": "Add location marker to note"}
        }
    },
    "edit": {
        "help": "Create note",
        "arguments": {
            "--note": {"help": "Set note title"},
            "--title": {"help": "Set note title"},
            "--body": {"help": "Set note content"},
            "--tags": {"help": "Add tag to note"},
            "--notepad": {"help": "Add location marker to note"}
        }
    },
    "remove": {
        "help": "Create note",
        "arguments": {
            "--note": {"help": "Set note title"},
        }
    },
    "show": {
        "help": "Create note",
        "arguments": {
            "--note": {"help": "Set note title"},
        }
    },
    "find": {
        "help": "Create note",
        "arguments": {
            "--search": {"help": "Add tag to note"},
            "--tags": {"help": "Add tag to note"},
            "--notepads": {"help": "Add location marker to note"},
            "--date": {"help": "Add location marker to note"},
            "--count": {"help": "Add location marker to note"},
        },
        "flags": {
            "--exact-entry": {"help": "Add tag to note", "value": True, "default": False},
            "--content-search": {"help": "Add tag to note", "value": True, "default": False},
            "--url-only": {"help": "Add tag to note"},
        }
    },
    # Notebooks
    "list-notepad": {
        "help": "Create note",
    },
    "create-notepad": {
        "help": "Create note",
        "arguments": {
            "--title": {"help": "Set note title"},
        }
    },
    "edit-notepad": {
        "help": "Create note",
        "arguments": {
            "--notepad": {"help": "Set note title"},
            "--title": {"help": "Set note title"},
        }
    },
    "remove-notepad": {
        "help": "Create note",
        "arguments": {
            "--notepad": {"help": "Set note title"},
        }
    },
}

LVL = len(sys.argv[1:])
INPUT = sys.argv[1:]
#список команд
CMD_LIST = COMMANDS.keys()
# введенная команда
CMD = None if LVL == 0 else INPUT[0]
# список возможных аргументов введенной команды
CMD_ARGS  = COMMANDS[CMD]['arguments'] if LVL > 0 and COMMANDS.has_key(CMD) and COMMANDS[CMD].has_key('arguments') else {}
# список возможных флагов введенной команды
CMD_FLAGS = COMMANDS[CMD]['flags'] if LVL > 0 and COMMANDS.has_key(CMD) and COMMANDS[CMD].has_key('flags') else {}
# список введенных аргументов и их значений
INP = [] if LVL <= 1 else INPUT[1:]

logging.debug("CMD_LIST : %s", str(CMD_LIST))
logging.debug("CMD: %s", str(CMD))
logging.debug("CMD_ARGS : %s", str(CMD_ARGS))
logging.debug("CMD_FLAGS : %s", str(CMD_FLAGS))
logging.debug("INP : %s", str(INP))

def parse():
    INP_DATA = {}

    if CMD == "--help":
        printHelp()

    if CMD is None or not COMMANDS.has_key(CMD):
        printErrorCommand()

    if "--help" in INP:
        printHelp()

    # подготовка к парсингу
    for arg, params in (CMD_ARGS.items() + CMD_FLAGS.items()):
        # установка значений по умолчаеию
        if params.has_key('default'):
            INP_DATA[arg] = params['default']

        # проверка, присутствует ли необходимый аргумент запросе
        if params.has_key('required') and arg not in INP:
            printErrorArgument(arg)

    activeArg = None
    for item in INP:
        # Проверяем что ожидаем аргумент
        if activeArg is None:
            # Действия для аргумента
            if CMD_ARGS.has_key(item):
                activeArg = item

            # Действия для флага
            elif CMD_FLAGS.has_key(item):
                INP_DATA[item] = CMD_FLAGS[item]["value"]

            # Ошибка параметр не найден
            else:
                printErrorArgument(item)

        else:
            # Ошибка значения является параметром
            if CMD_ARGS.has_key(item) or CMD_FLAGS.has_key(item):
                printErrorArgument(activeArg, item)

            INP_DATA[activeArg] = item
            activeArg = None

    if activeArg is not None:
        printErrorArgument(activeArg, "")

    # trim -- and ->_
    INP_DATA = dict([key.lstrip("-").replace("-", "_"), val] for key, val in INP_DATA.items() )
    return INP_DATA


def printAutocomplete():

    def printGrid(list):
        print " ".join(list)

    # последнее веденное значение
    LAST_VAL = INP[-1] if LVL > 1 else None
    PREV_LAST_VAL = INP[-2] if LVL > 2 else None
    ARGS_FLAGS_LIST = CMD_ARGS.keys()+CMD_FLAGS.keys()

    # печатаем корневые команды
    if CMD is None:
        printGrid(CMD_LIST)

    # работа с корневыми командами
    elif not INP:

        # печатаем аргументы если команда найдена
        if CMD in CMD_LIST:
            printGrid(ARGS_FLAGS_LIST)

        # автозаполнение для неполной команды
        else:
            # фильтруем команды подходящие под введенный шаблон
            printGrid([item for item in CMD_LIST if item.startswith(CMD)])

    # обработка аргументов
    else:

        # фильтруем аргументы которые еще не ввели
        if CMD_ARGS.has_key(PREV_LAST_VAL) or CMD_FLAGS.has_key(LAST_VAL) :
            printGrid([item for item in ARGS_FLAGS_LIST if item not in INP]) 

        # автозаполнение для неполной команды
        elif not CMD_ARGS.has_key(PREV_LAST_VAL):
            printGrid([item for item in ARGS_FLAGS_LIST if item not in INP and item.startswith(LAST_VAL)])

        # обработка аргумента
        else:
            print "" #"Please_input_%s" % INP_ARG.replace('-', '')

def printErrorCommand():
    io.printLine('Unexpected command "%s"' % (CMD))
    printHelp()

def printErrorArgument(errorArg, errorVal=None):
    
    if errorVal is None:
        io.printLine('Unexpected argument "%s" for command "%s"' % (errorArg, CMD))
    else:
        io.printLine('Unexpected value "%s" for argument "%s"' % (errorVal, errorArg))
    printHelp()

def printHelp():
    if CMD is None or not COMMANDS.has_key(CMD):
        tab = len(max(COMMANDS.keys(), key=len))
        io.printLine("Available commands:")
        for cmd in COMMANDS:
            io.printLine("%s : %s" % (cmd.rjust(tab, " "), COMMANDS[cmd]['help']))

    else:

        tab = len(max(CMD_ARGS.keys()+CMD_FLAGS.keys(), key=len))

        io.printLine("Options for: %s" % CMD)
        io.printLine("Avaible arguments:")
        for arg in CMD_ARGS:
            io.printLine("%s : %s" % (arg.rjust(tab, " "), CMD_ARGS[arg]['help']))

        io.printLine("Avaible flags:")
        for flag in CMD_FLAGS:
            io.printLine("%s : %s" % (flag.rjust(tab, " "), CMD_FLAGS[flag]['help']))
    exit(1)