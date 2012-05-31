# -*- coding: utf-8 -*-
import sys

def printGrid(list):
    print " ".join(list)
    #print "".join([item.ljust(12, " ") + ("\n" if index%4 == 3 else "") for index, item in enumerate(list)])

COMMANDS = {
    "create": ["--title", "--body", "--tag", "--location"],
    "edit": ["--id", "--title", "--body", "--tag", "--location"],
    "remove": ["--id"],
    "find": ["--tag", "--notepad", "--force", "--exact-entry", "--count", "--url-only"],
    "fix": [],
}

input = sys.argv[2:]

#input = ["autocomplete.py", ]
#input = ["autocomplete.py", "create"]
#input = ["autocomplete.py", "create", "--title"]
#input = ["autocomplete.py", "create", "--t"]
#input = ["autocomplete.py", "create", "--title", "New title", "--body", "New note"]
#input = ["autocomplete.py", "create", "--title", "New title", "--body", "New note", "--tag"]
#input = ["autocomplete.py", "find", '--']

level = len(input)

#список команд
CMD_LIST = COMMANDS.keys()
# введенная команда
CMD = None if level == 0 else input[0]
# список возможных аргументов введенной команды
ARGS = [] if level == 0 or not COMMANDS.has_key(CMD) else COMMANDS[CMD]
# список введенных аргументов и их значений
INP = [] if level <= 1 else input[1:]

# список введенных аргументов (без значений)
INP_ARGS = INP[::2] if INP else []
# последний введенный аргумент
INP_ARG = INP[-1] if len(INP)%2 == 1 else ( INP[-2] if INP else None )
# последнее веденное значение
INP_VAL = INP[-1] if INP and len(INP)%2 == 0 else None

# печатаем корневые команды
if level == 0:
    printGrid(CMD_LIST)

# работа с корневыми командами
elif level == 1:

    # печатаем аргументы если команда найдена
    if CMD in CMD_LIST:
        printGrid(ARGS)

    # автозаполнение для неполной команды
    else:
        # фильтруем команды подходящие под введенный шаблон
        printGrid([item for item in CMD_LIST if item.startswith(CMD)])

# обработка аргументов
else:

    if INP_VAL:
        # фильтруем аргументы которые еще не ввели
        printGrid([item for item in ARGS if item not in INP_ARGS])

    else:
        # автозаполнение для неполной команды
        if INP_ARG not in ARGS:
            printGrid([item for item in ARGS if item not in INP_ARGS and item.startswith(INP_ARG)])

        # обработка аргумента
        else:
            print "" #"Please_input_%s" % INP_ARG.replace('-', '')