#!/usr/bin/python3

from actilib.imquest.reporting import generate_report
from actilib.helpers.general import load_test_data

data = load_test_data()
generate_report(data, 'imquest_test_report.pdf')
