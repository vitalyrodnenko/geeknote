# -*- coding: utf-8 -*-
import getpass


def GetUserCredentials():
    """Prompts the user for a username and password."""
    email = None #fill these in during testing if you want
    password = None
    if email is None:
        email = raw_input("Email: ")
        
    if password is None:
        password_prompt = "Password for %s: " % email
        password = getpass.getpass(password_prompt)

    return (email, password)