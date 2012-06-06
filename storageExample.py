from storage import *

# storage object
s = Storage()

# search
from oauth import GeekNoteAuth
GNA = GeekNoteAuth()
s.setSearch(GNA)
s.getSearch()

# notebooks
tags = ['notebook1', 'notebook2']
s.setNotebooks(tags)
s.getNotebooks()

# tags
tags = ['tag1', 'tag2', 'tag3']
s.setTags(tags)
s.getTags()

# settings
data = {'k1': 'v1', 'k2': 'v2', 'mykey': 'my new value'}
s.setSettings(data)
s.getSettings()