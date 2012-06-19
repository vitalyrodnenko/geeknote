class T(object):
    
    def __getattr__(self, name):
        return self.test

    def test(self, *args, **kwargs):
        print args, kwargs

x = T()
x.tmp(1, 2, 3)