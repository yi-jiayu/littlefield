# littlefield
Python SDK for the Littlefield simulation game

## Demo
[![asciicast](https://asciinema.org/a/165140.png)](https://asciinema.org/a/165140)

## Installation
```pip install git+https://github.com/yi-jiayu/littlefield.git```

## Authentication
1. Provide your Team ID and password directly when creating a `Littlefield` object:
```
from littlefield import Littlefield

lf = Littlefield('team_id', 'password')
```
2. Use the `LITTLEFIELD_TEAM_ID` and `LITTLEFIELD_PASSWORD` environment variables:
```
# LITTLEFIELD_TEAM_ID=team_id
# LITTLEFIELD_PASSWORD=password

from littlefield import Littlefield

lf = Littlefield()
```

## Examples
```
from littlefield import Littlefield

lf = Littlefield()  # get credentials from environment
print(lf.cash())
print(lf.orders.info())
print(lf.orders.job_arrivals())
print(lf.materials.info())
print(lf.materials.inventory())
print(lf.station1.info())
print(lf.station1.queue_size())
print(lf.completed_jobs.lead_times())
```

## Docs
Coming soon!
