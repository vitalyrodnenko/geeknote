# -*- coding: utf-8 -*-

from log import logging
import out


COMMANDS_DICT = {
    # User
    "user": {
        "help": "Show information about active user.",
        "flags": {
            "--full": {"help": "Show full information.",
                       "value": True,
                       "default": False},
        }
    },
    "login": {
        "help": "Authorize in Evernote.",
    },
    "logout": {
        "help": "Logout from Evernote.",
        "flags": {
            "--force": {"help": "Don't ask about logging out.",
                        "value": True,
                        "default": False},
        }
    },
    "settings": {
        "help": "Show and edit current settings.",
        "arguments": {
            "--editor": {"help": "Set the editor, which use to "
                                 "edit and create notes.",
                         "emptyValue": '#GET#'},
        }
    },

    # Notes
    "create": {
        "help": "Create note in evernote.",
        "arguments": {
            "--title":      {"altName": "-t",
                             "help": "The note title.",
                             "required": True},
            "--content":    {"altName": "-c",
                             "help": "The note content.",
                             "required": True},
            "--tags":       {"altName": "-tg",
                             "help": "One tag or the list of tags which"
                                     " will be added to the note."},
            "--notebook":   {"altName": "-nb",
                             "help": "Set the notebook where to save note."}
        }
    },
    "edit": {
        "help": "Edit note in Evernote.",
        "firstArg": "--note",
        "arguments": {
            "--note":       {"altName": "-n",
                             "help": "The name or ID from the "
                                     "previous search of a note to edit."},
            "--title":      {"altName": "-t",
                             "help": "Set new title of the note."},
            "--content":    {"altName": "-c",
                             "help": "Set new content of the note."},
            "--tags":       {"altName": "-tg",
                             "help": "Set new list o tags for the note."},
            "--notebook":   {"altName": "-nb",
                             "help": "Assign new notebook for the note."}
        }
    },
    "remove": {
        "help": "Remove note from Evernote.",
        "firstArg": "--note",
        "arguments": {
            "--note":  {"altName": "-n",
                        "help": "The name or ID from the previous "
                                "search of a note to remove."},
        },
        "flags": {
            "--force": {"altName": "-f",
                        "help": "Don't ask about removing.",
                        "value": True,
                        "default": False},
        }
    },
    "show": {
        "help": "Output note in the terminal.",
        "firstArg": "--note",
        "arguments": {
            "--note": {"altName": "-n",
                       "help": "The name or ID from the previous "
                               "search of a note to show."},
        }
    },
    "find": {
        "help": "Search notes in Evernote.",
        "firstArg": "--search",
        "arguments": {
            "--search":     {"altName": "-s",
                             "help": "Text to search.",
                             "emptyValue": "*"},
            "--tags":       {"altName": "-tg",
                             "help": "Notes with which tag/tags to search."},
            "--notebooks":  {"altName": "-nb",
                             "help": "In which notebook search the note."},
            "--date":       {"altName": "-d",
                             "help": "Set date in format dd.mm.yyyy or "
                                     "date range dd.mm.yyyy-dd.mm.yyyy."},
            "--count":      {"altName": "-cn",
                             "help": "How many notes show in the result list.",
                             "type": int},
        },
        "flags": {
            "--with-url":       {"altName": "-wu",
                                 "help": "Add direct url of each note "
                                         "in results to Evernote web-version.",
                                 "value": True,
                                 "default": False},
            "--exact-entry":    {"altName": "-ee",
                                 "help": "Search for exact "
                                         "entry of the request.",
                                 "value": True,
                                 "default": False},
            "--content-search": {"altName": "-cs",
                                 "help": "Search by content, not by title.",
                                 "value": True,
                                 "default": False},
        }
    },

    # Notebooks
    "notebook-list": {
        "help": "Show the list of existing notebooks in your Evernote.",
    },
    "notebook-create": {
        "help": "Create new notebook.",
        "arguments": {
            "--title": {"altName": "-t",
                        "help": "Set the title of new notebook."},
        }
    },
    "notebook-edit": {
        "help": "Edit/rename notebook.",
        "firstArg": "--notebook",
        "arguments": {
            "--notebook":   {"altName": "-nb",
                             "help": "The name of a notebook to rename."},
            "--title":      {"altName": "-t",
                             "help": "Set the new name of notebook."},
        }
    },

    # Tags
    "tag-list": {
        "help": "Show the list of existing tags in your Evernote.",
    },
    "tag-create": {
        "help": "Create new tag.",
        "arguments": {
            "--title": {"altName": "-t", "help": "Set the title of new tag."},
        }
    },
    "tag-edit": {
        "help": "Edit/rename tag.",
        "firstArg": "--tagname",
        "arguments": {
            "--tagname":    {"altName": "-tgn",
                             "help": "The name of a tag to rename."},
            "--title":      {"altName": "-t",
                             "help": "Set the new name of tag."},
        }
    },
}
"""
    "tag-remove": {
        "help": "Remove tag.",
        "firstArg": "--tagname",
        "arguments": {
            "--tagname": {"help": "The name of a tag to remove."},
        },
        "flags": {
            "--force": {"help": "Don't ask about removing.", "value": True, "default": False},
        }
    },
    "notebook-remove": {
        "help": "Remove notebook.",
        "firstArg": "--notebook",
        "arguments": {
            "--notebook": {"help": "The name of a notebook to remove."},
        },
        "flags": {
            "--force": {"help": "Don't ask about removing.", "value": True, "default": False},
        }
    },
"""


class argparser(object):

    COMMANDS = COMMANDS_DICT
    sys_argv = None

    def __init__(self, sys_argv):
        self.sys_argv = sys_argv
        self.LVL = len(sys_argv)
        self.INPUT = sys_argv

        # list of commands
        self.CMD_LIST = self.COMMANDS.keys()
        # command
        self.CMD = None if self.LVL == 0 else self.INPUT[0]
        # list of possible arguments of the command line
        self.CMD_ARGS = self.COMMANDS[self.CMD]['arguments'] if self.LVL > 0 and self.CMD in self.COMMANDS and 'arguments' in self.COMMANDS[self.CMD] else {}
        # list of possible flags of the command line
        self.CMD_FLAGS = self.COMMANDS[self.CMD]['flags'] if self.LVL > 0 and self.CMD in self.COMMANDS and 'flags' in self.COMMANDS[self.CMD] else {}
        # list of entered arguments and their values
        self.INP = [] if self.LVL <= 1 else self.INPUT[1:]

        logging.debug("CMD_LIST : %s", str(self.CMD_LIST))
        logging.debug("CMD: %s", str(self.CMD))
        logging.debug("CMD_ARGS : %s", str(self.CMD_ARGS))
        logging.debug("CMD_FLAGS : %s", str(self.CMD_FLAGS))
        logging.debug("INP : %s", str(self.INP))

    def parse(self):
        self.INP_DATA = {}

        if self.CMD is None:
            out.printAbout()
            return False

        if self.CMD == "autocomplete":
            # подставляем аргументы для автозаполнения
            # делаем смещение на 1 аргумент, т.к. 1 это autocomplete
            self.__init__(self.sys_argv[1:])
            self.printAutocomplete()
            return False

        if self.CMD == "--help":
            self.printHelp()
            return False

        if self.CMD not in self.COMMANDS:
            self.printErrorCommand()
            return False

        if "--help" in self.INP:
            self.printHelp()
            return False

        # prepare data
        for arg, params in (self.CMD_ARGS.items() + self.CMD_FLAGS.items()):
            # set values by default
            if 'default' in params:
                self.INP_DATA[arg] = params['default']

            # replace `altName` entered arguments on full
            if 'altName' in params and params['altName'] in self.INP:
                self.INP[self.INP.index(params['altName'])] = arg

        activeArg = None
        ACTIVE_CMD = None
        # check and insert first argument by default
        if 'firstArg' in self.COMMANDS[self.CMD]:
            firstArg = self.COMMANDS[self.CMD]['firstArg']
            if len(self.INP) > 0:
                # смотрим что первое знаение не аргумент по умолчанию,
                # а другой аргумент
                if self.INP[0] not in (self.CMD_ARGS.keys() +
                                       self.CMD_FLAGS.keys()):
                    self.INP = [firstArg, ] + self.INP
            else:
                self.INP = [firstArg, ]

        for item in self.INP:
            # check what are waiting the argument
            if activeArg is None:
                # Действия для аргумента
                if item in self.CMD_ARGS:
                    activeArg = item
                    ACTIVE_CMD = self.CMD_ARGS[activeArg]

                # actions for the flag
                elif item in self.CMD_FLAGS:
                    self.INP_DATA[item] = self.CMD_FLAGS[item]["value"]

                # error. parameter is not found
                else:
                    self.printErrorArgument(item)
                    return False

            else:
                activeArgTmp = None
                # values it is parameter
                if item in self.CMD_ARGS or item in self.CMD_FLAGS:
                    # "Активный" аргумент имеет параметр emptyValue
                    if "emptyValue" in ACTIVE_CMD:
                        activeArgTmp = item  # запоминаем новый "активный" аргумент
                        item = ACTIVE_CMD['emptyValue']  # подменяем значение на emptyValue
                    # Ошибка, "активный" аргумент не имеет значений
                    else:
                        self.printErrorArgument(activeArg, item)
                        return False

                if 'type' in ACTIVE_CMD:
                    convType = ACTIVE_CMD['type']
                    if convType not in (int, str):
                        logging.error("Unsupported argument type: %s", convType)
                        return False

                    try:
                        item = convType(item)
                    except:
                        self.printErrorArgument(activeArg, item)
                        return False

                self.INP_DATA[activeArg] = item
                activeArg = activeArgTmp  # тут или пусто, или новый "активный" аргумент

        # если остались "активные" аршументы
        if activeArg is not None:
            # если есть параметр emptyValue
            if 'emptyValue' in ACTIVE_CMD:
                self.INP_DATA[activeArg] = ACTIVE_CMD['emptyValue']

            # инече ошибка
            else:
                self.printErrorArgument(activeArg, "")
                return False

        # проверка, присутствует ли необходимый аргумент запросе
        for arg, params in (self.CMD_ARGS.items() + self.CMD_FLAGS.items()):
            if 'required' in params and arg not in self.INP:
                self.printErrorReqArgument(arg)
                return False

        # trim -- and ->_
        self.INP_DATA = dict([key.lstrip("-").replace("-", "_"), val] for key, val in self.INP_DATA.items())
        return self.INP_DATA

    def printAutocomplete(self):
        # последнее веденное значение
        LAST_VAL = self.INP[-1] if self.LVL > 1 else None
        PREV_LAST_VAL = self.INP[-2] if self.LVL > 2 else None
        ARGS_FLAGS_LIST = self.CMD_ARGS.keys() + self.CMD_FLAGS.keys()

        # печатаем корневые команды
        if self.CMD is None:
            self.printGrid(self.CMD_LIST)

        # работа с корневыми командами
        elif not self.INP:

            # печатаем аргументы если команда найдена
            if self.CMD in self.CMD_LIST:
                self.printGrid(ARGS_FLAGS_LIST)

            # автозаполнение для неполной команды
            else:
                # фильтруем команды подходящие под введенный шаблон
                self.printGrid([item for item in self.CMD_LIST if item.startswith(self.CMD)])

        # обработка аргументов
        else:

            # фильтруем аргументы которые еще не ввели
            if PREV_LAST_VAL in self.CMD_ARGS or LAST_VAL in self.CMD_FLAGS:
                self.printGrid([item for item in ARGS_FLAGS_LIST if item not in self.INP])

            # autocomplete for part of the command
            elif PREV_LAST_VAL not in self.CMD_ARGS:
                self.printGrid([item for item in ARGS_FLAGS_LIST if item not in self.INP and item.startswith(LAST_VAL)])

            # processing of the arguments
            else:
                print ""  # "Please_input_%s" % INP_ARG.replace('-', '')

    def printGrid(self, list):
        out.printLine(" ".join(list))

    def printErrorCommand(self):
        out.printLine('Unexpected command "%s"' % (self.CMD))
        self.printHelp()

    def printErrorReqArgument(self, errorArg):
        out.printLine('Not found required argument "%s" '
                      'for command "%s" ' % (errorArg, self.CMD))
        self.printHelp()

    def printErrorArgument(self, errorArg, errorVal=None):
        if errorVal is None:
            out.printLine('Unexpected argument "%s" '
                          'for command "%s"' % (errorArg, self.CMD))
        else:
            out.printLine('Unexpected value "%s" '
                          'for argument "%s"' % (errorVal, errorArg))
        self.printHelp()

    def printHelp(self):
        if self.CMD is None or self.CMD not in self.COMMANDS:
            tab = len(max(self.COMMANDS.keys(), key=len))
            out.printLine("Available commands:")
            for cmd in self.COMMANDS:
                out.printLine("%s : %s" % (cmd.rjust(tab, " "),
                                           self.COMMANDS[cmd]['help']))

        else:

            tab = len(max(self.CMD_ARGS.keys() +
                          self.CMD_FLAGS.keys(), key=len))

            out.printLine("Options for: %s" % self.CMD)
            out.printLine("Available arguments:")
            for arg in self.CMD_ARGS:
                out.printLine("%s : %s%s" % (
                    arg.rjust(tab, " "),
                    '[default] ' if 'firstArg' in self.COMMANDS[self.CMD] and self.COMMANDS[self.CMD]['firstArg'] == arg else '',
                    self.CMD_ARGS[arg]['help']))

            if self.CMD_FLAGS:
                out.printLine("Available flags:")
                for flag in self.CMD_FLAGS:
                    out.printLine("%s : %s" % (flag.rjust(tab, " "),
                                               self.CMD_FLAGS[flag]['help']))
