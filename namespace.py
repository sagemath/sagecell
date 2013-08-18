from collections import defaultdict
class InstrumentedNamespace(dict):
    def __init__(self, *args, **kwargs):
        """
        Set up a namespace id
        """
        dict.__init__(self,*args,**kwargs)
        self.events = defaultdict(lambda: defaultdict(list))
        
    def on(self, key, event, f):
        self.events[key][event].append(f)

    def off(self, key, event=None, f=None):
        if event is None:
            self.events.pop(key,None)
        elif f is None:
            self.events[key].pop(event,None)
        else:
            self.events[key][event].remove(f)

    def trigger(self, key, event, *args, **kwargs):
        if key in self.events and event in self.events[key]:
            for f in self.events[key][event]:
                f(key, *args, **kwargs)

    def __setitem__(self, key, value):
        """
        Set a value in the dictionary and run attached notification functions.
        """
        init = False
        if key not in self:
            self.trigger(key, 'initialize', value)
        dict.__setitem__(self, key, value)
        self.trigger(key, 'change', value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.off(key)
