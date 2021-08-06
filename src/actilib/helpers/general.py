import json
import numpy as np
import os.path
import pkgutil


def load_test_data():
    return json.loads(pkgutil.get_data('actilib', os.path.join('../resources', 'test_data.json')).decode("utf-8"))


class ListBuffer:
    """
    Store lists of values and returns element-wise statistical properties.

    Useful to average data series and plot them with error bars.
    """

    def __init__(self):
        self.vectors = None

    def add_value_list(self, values_list):
        if self.vectors is None:
            self.vectors = np.array(values_list)
        else:
            self.vectors = np.vstack((self.vectors, values_list))

    def mean(self):
        return np.mean(self.vectors, axis=0)

    def std(self):
        return np.std(self.vectors, axis=0)

    def se(self):
        return np.std(self.vectors, axis=0) / np.sqrt(len(self.vectors))
