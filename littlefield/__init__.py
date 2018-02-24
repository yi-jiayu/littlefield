import requests
import re
import os

from collections import namedtuple
from enum import Enum

session_id_regex = re.compile('JSESSIONID=(\w+);')
points_regex = re.compile("points: '((?:\d+ [\d.]+ ?)+)'")
orders_info_regex = re.compile(r'''<b>Maximum WIP Limit: </b>(\d+) jobs<BR>
<B>Number of kits in 1 job: </B>(\d+)<BR>
<B>Lot size: </B>(\d+) kits, or (\d+) lots? per job<BR>
<B>Current contract: </B>(\d+)<BR>
<DD>Quoted lead time: ([\d.]+) day\(s\)<BR>
<DD>Maximum lead time: ([\d.]+) day\(s\)<BR>
<DD>Revenue per order: ([\d.]+) dollars<BR><HR>''')
materials_info_regex = re.compile(r'''<BR><B>Unit Cost: </B> \$ ([\d.]+)
<BR><B>Order Cost: </B> \$ ([\d.]+)
<BR><B>Lead Time:</B> (\d+) day\(s\)
<BR><B>Reorder Point:</B> ([\d,]+) kits
\( (\d+) batches of (\d+) \)
<BR><B>Order Quantity:</B>
([\d,]+) kits
\( (\d+) batches of (\d+) \)
(?:<P><B>Material order of ([\d,]+)\s+kits due to arrive in ([\d.]+) simulated days)?''')
station_info_regex = re.compile(r'''<P><B> Number of Machines: </B>(\d+)<BR>
<B>Scheduling Policy: </B>(\w+)<BR>
<B>Purchase Price: </B>\$ ([\d,]+)<BR>
<B>Retirement Price: </B>\$ ([\d,]+)<BR>''')


class Data(Enum):
    JOBS_IN = 'JOBIN'
    QUEUED_JOBS = 'JOBQ'
    INVENTORY = 'INV'
    STATION1_QUEUE_SIZE = 'S1Q'
    STATION1_UTILISATION = 'S1UTIL'
    STATION2_QUEUE_SIZE = 'S3Q'
    STATION2_UTILISATION = 'S3UTIL'
    STATION3_QUEUE_SIZE = 'S3Q'
    STATION3_UTILISATION = 'S3UTIL'
    COMPLETED_JOB_COUNT = 'JOBOUT'
    LEAD_TIMES = 'JOBT'
    REVENUES = 'JOBREV'
    CASH = 'CASH'


OrdersInfo = namedtuple('OrdersInfo',
                        ['wip_limit', 'kits_per_job', 'lot_size', 'lots_per_job', 'current_contract',
                         'quoted_lead_time', 'max_lead_time', 'revenue_per_order'])


def parse_orders_info(wip_limit, kits_per_job, lot_size, lots_per_job, current_contract, quoted_lead_time,
                      max_lead_time, revenue_per_order):
    wip_limit = int(wip_limit)
    kits_per_job = int(kits_per_job)
    lot_size = int(lot_size)
    lots_per_job = int(lots_per_job)
    current_contract = int(current_contract)
    quoted_lead_time = float(quoted_lead_time)
    max_lead_time = float(max_lead_time)
    revenue_per_order = float(revenue_per_order)
    return OrdersInfo(wip_limit, kits_per_job, lot_size, lots_per_job, current_contract, quoted_lead_time,
                      max_lead_time, revenue_per_order)


MaterialsInfo = namedtuple('MaterialsInfo',
                           ['unit_cost', 'order_cost', 'lead_time', 'reorder_point', 'reorder_point_batches',
                            'reorder_point_batch_size', 'order_quantity', 'order_quantity_batches',
                            'order_quantity_batch_size',
                            'next_arrival_quantity', 'next_arrival_eta'])


def parse_materials_info(unit_cost, order_cost, lead_time, reorder_point, reorder_point_batches,
                         reorder_point_batch_size, order_quantity, order_quantity_batches, order_quantity_batch_size,
                         next_arrival_quantity=None, next_arrival_eta=None):
    unit_cost = float(unit_cost)
    order_cost = float(order_cost)
    lead_time = int(lead_time)
    reorder_point = int(reorder_point.replace(',', ''))
    reorder_point_batches = int(reorder_point_batches)
    reorder_point_batch_size = int(reorder_point_batch_size)
    order_quantity = int(order_quantity.replace(',', ''))
    order_quantity_batches = int(order_quantity_batches)
    order_quantity_batch_size = int(order_quantity_batch_size)
    if next_arrival_quantity is not None:
        next_arrival_quantity = int(next_arrival_quantity.replace(',', ''))
    if next_arrival_eta is not None:
        next_arrival_eta = float(next_arrival_eta)

    return MaterialsInfo(unit_cost, order_cost, lead_time, reorder_point, reorder_point_batches,
                         reorder_point_batch_size, order_quantity, order_quantity_batches, order_quantity_batch_size,
                         next_arrival_quantity, next_arrival_eta)


StationInfo = namedtuple('StationInfo', ['num_machines', 'scheduling_policy', 'purchase_price', 'retirement_price'])


def parse_station_info(num_machines, scheduling_policy, purchase_price, retirement_price):
    num_machines = int(num_machines)
    purchase_price = float(purchase_price.replace(',', ''))
    retirement_price = float(retirement_price.replace(',', ''))

    return StationInfo(num_machines, scheduling_policy, purchase_price, retirement_price)


class Littlefield:
    def __init__(self, team_id='', password=''):
        if team_id == '' or password == '':
            self.team_id, self.password = Littlefield._get_credentials_from_environment()
        else:
            self.team_id = team_id
            self.password = password
        self.session_id = self._get_session_id()

        self.orders = Orders(self)
        self.materials = Materials(self)
        self.station1 = Station(self, 1)
        self.station2 = Station(self, 2)
        self.station3 = Station(self, 3)
        self.completed_jobs = CompletedJobs(self)

    @staticmethod
    def _get_credentials_from_environment():
        un = os.getenv('LITTLEFIELD_TEAM_ID', '')
        pw = os.getenv('LITTLEFIELD_PASSWORD', '')
        return un, pw

    def _get_session_id(self):
        headers = {'User-Agent': ''}
        payload = {'institution': 'sharma', 'ismobile': 'false', 'id': self.team_id, 'password': self.password}
        r = requests.post('http://op.responsive.net/Littlefield/CheckAccess', headers=headers, data=payload)
        cookie = r.headers.get('Set-Cookie')
        m = session_id_regex.search(cookie)
        if m is None:
            raise RuntimeError(r.text)

        return m.group(1)

    def _get(self, path, params=None):
        cookie = {'JSESSIONID': self.session_id}
        r = requests.get('http://op.responsive.net/Littlefield/' + path, cookies=cookie, params=params)
        return r.text

    def _get_data(self, data, x='all'):
        if isinstance(data, Enum):
            data = data.value

        raw = self._get('Plot?data={}&x={}'.format(data, x))
        m = points_regex.search(raw)
        if m is None:
            raise RuntimeError('failed to extract data')

        data = m.group(1)
        return list(self._to_points(data))

    @staticmethod
    def _to_points(data):
        points = [float(x) for x in data.split(' ')]
        for i in range(0, len(points), 2):
            yield points[i], points[i + 1]


class Orders:
    def __init__(self, lf):
        self.lf = lf

    def job_arrivals(self, x='all'):
        return self.lf._get_data(Data.JOBS_IN, x)

    def queued_jobs(self, x='all'):
        return self.lf._get_data(Data.QUEUED_JOBS, x)

    def info(self, update=False) -> OrdersInfo:
        params = {update: 'update'} if update else None
        raw = self.lf._get('OrdersMenu', params)
        m = orders_info_regex.search(raw)
        if m is None:
            print(raw)
            raise RuntimeError('failed to get customer orders')

        return parse_orders_info(*m.groups())


class Materials:
    def __init__(self, lf):
        self.lf = lf

    def inventory(self, x='all'):
        return self.lf._get_data(Data.INVENTORY, x)

    def info(self, update=False) -> MaterialsInfo:
        params = {update: 'update'} if update else None
        raw = self.lf._get('MaterialMenu', params)
        m = materials_info_regex.search(raw)
        if m is None:
            raise RuntimeError('failed to get material info')

        return parse_materials_info(*m.groups())


class Station:
    def __init__(self, lf, id):
        self.lf = lf
        self.id = id

    def queue_size(self, x='all'):
        return self.lf._get_data('S{}Q'.format(self.id), x)

    def utilization(self, x='all'):
        return self.lf._get_data('S{}UTIL'.format(self.id), x)

    def info(self, update=False) -> StationInfo:
        params = {update: 'update'} if update else None
        raw = self.lf._get('StationMenu?id={}'.format(self.id), params)
        m = station_info_regex.search(raw)
        if m is None:
            raise RuntimeError('failed to get station info')

        return parse_station_info(*m.groups())


class CompletedJobs:
    def __init__(self, lf):
        self.lf = lf

    def count(self, x='all'):
        return self.lf._get_data(Data.COMPLETED_JOB_COUNT, x)

    def lead_times(self, x='all'):
        return self.lf._get_data(Data.LEAD_TIMES, x)

    def revenues(self, x='all'):
        return self.lf._get_data(Data.REVENUES, x)
