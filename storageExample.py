from storage import *

# storage object
s = Storage()

# search
search = [
    {'uuid': '646-64564-324-53', 'name': 'note1', 'stype': 'note', 'snippet': 'Snippet for note1'},
    {'uuid': '645423-546546-45353', 'name': 'notebook2', 'stype': 'noteebook', 'snippet': 'Snippet for notebook2'}
]

s.setSearch(search)
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