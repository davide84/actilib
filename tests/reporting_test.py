#!/usr/bin/python3

from actilib.reporting import *
from actilib.helpers import load_test_data


data = load_test_data()

# General data structure
# -----------------------------------------------------------------------------
print(data.keys())

# Software, phantom, series info
# -----------------------------------------------------------------------------
print(json.dumps(data['info_software'], indent=4, sort_keys=False))
print(json.dumps(data['info_phantom'], indent=4, sort_keys=False))
print(json.dumps(data['info_series'], indent=4, sort_keys=False))

# Detectability Index vs Phantom Size
# -----------------------------------------------------------------------------
plot_dprime_vs_size(data)

# Tube Current Profile
# -----------------------------------------------------------------------------
plot_current_profile(data)

# Noise Properties
# -----------------------------------------------------------------------------
plot_nps(data)
plot_normalized_nps(data)
plot_2d_nps(data)

# Resolution Properties
# -----------------------------------------------------------------------------
plot_ttf(data)
