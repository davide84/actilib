#!/usr/bin/python3

from actilib.imquest.reporting import generate_report
from actilib.helpers import load_test_data

data = load_test_data()
generate_report(data)
