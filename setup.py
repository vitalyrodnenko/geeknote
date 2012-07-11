from setuptools import setup

setup(
    name='geeknote',
    version='0.1',
    license='GPL',
    author='',
    author_email='',
    description='Geeknote - is a command line client for Evernote, that can be use on Linux, FreeBSD and OS X.',
    url='http://www.geeknote.me',
    packages=['lib', 'lib.evernote', 'lib.evernote.edam', 'lib.evernote.edam.error', 'lib.evernote.edam.limits',
              'lib.evernote.edam.notestore', 'lib.evernote.edam.type', 'lib.evernote.edam.userstore', 'geeknote'],
    install_requires=[
        'html2text',
        'sqlalchemy',
        'markdown',
        'thrift'
    ],
    entry_points={
        'console_scripts': [
            'geeknote = geeknote.geeknote:main',
            'gnsync = geeknote.gnsync:main'
        ]
    },
    platforms='Any',
    test_suite='unit'
)
