# CircularList by Basj see https://stackoverflow.com/a/40784706
# license: https://creativecommons.org/licenses/by-sa/4.0/
class CircularList(object):

    def __init__(self, size, data = []):
        """Initialization"""
        self.index = 0
        self.size = size
        self._data = list(data)[-size:]

    def append(self, value):
        """Append an element"""
        if len(self._data) == self.size:
            self._data[self.index] = value
        else:
            self._data.append(value)
        self.index = (self.index + 1) % self.size

    def __getitem__(self, key):
        """Get element by index, relative to the current index"""

        if len(self._data) == self.size:
            return(self._data[(key + self.index) % self.size])
        else:
            return(self._data[key])

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        """Return string representation"""
        return repr(self._data[self.index:] + self._data[:self.index]) + ' (' + str(len(self._data))+'/{} items)'.format(self.size)

import os

class History(CircularList):

    @classmethod
    def read(cls, filename):
        res = []
        try:
            os.stat(filename)
            f = open(filename, mode="r")
            res = f.readlines()
            f.close()
        except Exception as e:
            print("Error reading history")
            print(e)
        return res

    @classmethod
    def write(cls, filename, lines):
        with open(filename, mode="w") as f:
            for line in lines:
                if line != "":
                    f.write(line+"\n")
            f.flush()

    def __init__(self, size, widgets, filename="/data/history.txt"):
        self.filename = filename
        data = History.read(filename)
        while len(data) < size:
            data.append("")
        self.widgets = widgets
        self.dirty = False
        super().__init__(size, data)

    def save(self):
        if self.dirty:
            History.write(self.filename, self)
            self.dirty = False

    def append(self, value):
        super().append(value)
        self.dirty = True
        for i in range(len(self.widgets)):
            self.widgets[i].set_text(self[-(i+1)])

    def clear(self):
        try:
            for line in self.widgets:
                line.set_text("")
                super().append("")

            os.unlink(self.filename)
        except Exception as e:
            print(e)
