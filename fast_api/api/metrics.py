from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from config import settings


class MetricsClient:
    def __init__(self):
        self.url = settings.INFLUXDB_URL
        self.token = settings.INFLUXDB_TOKEN
        self.org = settings.INFLUXDB_ORG
        self.bucket = settings.INFLUXDB_BUCKET

    def _get_client(self) -> InfluxDBClientAsync:
        return InfluxDBClientAsync(url=self.url, token=self.token, org=self.org)

    async def write_kettle_state(self, current_temp: int, target_temp: int, status_code: int):
        if not self.token:
            return

        point = (
            Point("kettle_status")
            .tag("device_ip", settings.KETTLE_IP)
            .field("current_temp", float(current_temp))
            .field("target_temp", float(target_temp))
            .field("status_code", int(status_code))
        )

        async with self._get_client() as client:
            await client.write_api().write(bucket=self.bucket, record=point)

    async def get_data_for_period(self, hours: int) -> tuple[list[float], list[float], list[int]]:
        if not self.token:
            return [], [], []

        query = f"""
        from(bucket: "{self.bucket}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r._measurement == "kettle_status")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: false)
        """
        
        times = []
        temps = []
        statuses = []

        async with self._get_client() as client:
            result = await client.query_api().query(query=query)
            for table in result:
                for record in table.records:
                    times.append(record.get_time().timestamp())
                    temps.append(record.values.get("current_temp", 0.0))
                    statuses.append(record.values.get("status_code", 0))

        return times, temps, statuses

    async def get_energy_consumption(self, days: int) -> tuple[float, float]:
        if not self.token:
            return 0.0, 0.0

        query = f"""
        from(bucket: "{self.bucket}")
          |> range(start: -{days}d)
          |> filter(fn: (r) => r._measurement == "kettle_status")
          |> filter(fn: (r) => r._field == "status_code")
          |> sort(columns: ["_time"], desc: false)
        """

        total_heating_seconds = 0.0
        last_time = None
        last_status = 0

        async with self._get_client() as client:
            result = await client.query_api().query(query=query)
            for table in result:
                for record in table.records:
                    current_time = record.get_time().timestamp()
                    status = record.get_value()

                    if last_status in (1, 2) and last_time is not None:
                        diff = current_time - last_time
                        if diff < 300:
                            total_heating_seconds += diff

                    last_time = current_time
                    last_status = status

        kwh = (total_heating_seconds / 3600.0) * 1.8
        cost = kwh * 8.0
        return kwh, cost


metrics_client = MetricsClient()
