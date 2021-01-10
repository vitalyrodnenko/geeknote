HTTP proxy support for geeknote
===============================

I recommend to make this work with virtualenv, to avoid overwriting system files.
The important part is to install in the order **thrift, then evernote, then geeknote**. This will make sure that path search order is correct for thrift.

```
# Download thrift and geeknote
git clone https://github.com/apache/thrift.git
git clone https://github.com/mwilck/geeknote.git

# create and enter a virtual environment
virtualenv /var/tmp/geeknote
. /var/tmp/geeknote/bin/activate

# Apply proxy-support patches for thrift
cd thrift

## If the patches don't apply, you may need to check out the state that I wrote the patches for:
## git checkout -b proxy e363a34e63
curl https://issues.apache.org/jira/secure/attachment/12801233/0001-python-THttpClient-Add-support-for-system-proxy-sett.patch | git am
curl https://issues.apache.org/jira/secure/attachment/12801234/0002-Python-THttpClient-Support-proxy-authorization.patch | git am

# Install thrift from the patched tree
(cd lib/py; python setup.py install)
cd ..

# Install evernote
pip install evernote

# Install geeknote
cd geeknote
python setup.py install
```

Now `geeknote login`, `geeknote find`, etc. should work behind a proxy if the `http_proxy` environment variable is correctly set. You can now generate a script to activate the virtual environment:

```
cat >~/bin/geeknote <<\EOF
#! /bin/bash
. /var/tmp/geeknote/bin/activate
exec geeknote "$@"
EOF
chmod a+x ~/bin/geeknote
```