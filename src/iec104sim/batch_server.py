import c104
import time
import json
from datapoint import DataPoint
from pathlib import Path
from data_simulator import DataSimulator

app_time = 0

voltageDatapointIoAddresseses: set = {262177, 262178, 262179, 262180, 262181, 262182, 262183, 262184, 
                                      262186, 262188, 262190, 262192, 262194, 262196}
frequencyDatapointIoAddress: int = 262176
currentDatapointIoAddresses: set = {262220, 262221, 262222, 262223, 262224, 262226, 262228, 262230, 
                                    262232, 262234, 262236, 262244, 262245, 262246, 262247, 262252, 262253, 262254, 262255}

def convertMetaIoAddressToInt(point: c104.Point) -> int:
    metaAttr = str(getattr(point, "io_address", None))
    metaInt = int(metaAttr)
    return metaInt

def _simulate_for_meta(point) -> float:
    metaInt = convertMetaIoAddressToInt(point)
    if metaInt is None:
        return float(0)
    if metaInt == frequencyDatapointIoAddress:
        return DataSimulator.simulate_frequency()
    if metaInt in voltageDatapointIoAddresseses:
        return DataSimulator.simulate_voltage()
    if metaInt in currentDatapointIoAddresses:
        return DataSimulator.simulate_current(0, 16)
    return float(0)

def before_auto_transmit(point: c104.Point) -> None:
        point.value = _simulate_for_meta(point)
        print(f"{point.type} BEFORE AUTOMATIC REPORT on IOA: {point.io_address} VALUE: {point.value}")

def before_read(point: c104.Point) -> None:
        point.value = _simulate_for_meta(point)
        print("{0} BEFORE READ or INTERROGATION on IOA: {1} VALUE: {2}".format(point.type, point.io_address, point.value))

def load_datapoints_file(path: str | Path, start_io: int | None = None) -> dict[int, DataPoint]:

    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    out: dict[int, DataPoint] = {}
    next_io = start_io if start_io is not None else 1

    for name, obj in data.items():
        io = obj.get("IOAddress")
        if io is None:
            io = next_io
            next_io += 1
        
        dp = DataPoint(
            name=name,
            io_address=int(io),
            type_iec=obj.get("Type IEC") or obj.get("Type") or None,
            unit=obj.get("Unit / Einheit"),
            raw=obj
        )
        out[dp.io_address] = dp
    
    return out

def create_datapoints(station, json_path: str | Path = "Datapoints.json", start_io: int = 8, report_ms_default: int = 3000) -> dict[int, c104.Point]:
    json_path_obj = Path(json_path)
    json_file = json_path_obj if json_path_obj.is_absolute() else Path(__file__).with_name(json_path_obj.name)
    metas = load_datapoints_file(json_file, start_io=start_io)
    created: dict[int, c104.Point] = {}

    for io, meta in metas.items():
        
        dp = DataPoint(name=meta.name, io_address=io, type_iec=meta.type_iec, unit=meta.unit, raw=meta.raw)

        simulated_value = _simulate_for_meta(meta)
        if(simulated_value != 0):
            point = station.add_point(io_address=dp.io_address, type=c104.Type.M_ME_NC_1, report_ms=report_ms_default)

        point.value = simulated_value
        point.on_before_auto_transmit(callable=before_auto_transmit)
        point.on_before_read(callable=before_read)

        created[dp.io_address] = point

    return created

def main():
    server = c104.Server()
    station = server.add_station(common_address=47)
    assert station is not None, "Failed to add station to server"

    create_points = create_datapoints(station, json_path="Datapoints.json", start_io=8, report_ms_default=3000)
    
    pts = list(create_points.values())
    if not pts:
        print("No datapoints created, exiting")
        return
    
    selected = []
    seen = set()
    for p in pts[:10]:
        pid = id(p)
        if pid in seen:
            continue
        seen.add(pid)
        selected.append(p)
    try:
        batch = c104.Batch(cause=c104.Cot.SPONTANEOUS, points=pts[:10])
    except ValueError as e:
        print("Failed to create batch:", e)
        return

    print("Batch prepared with", len(batch.points) if hasattr(batch, "points") else len(selected))

    # start
    server.start()

    while not server.has_active_connections:
        print("Waiting for connection")
        time.sleep(1)

    time.sleep(1)

    print("transmit batch 1")
    server.transmit_batch(batch)

    time.sleep(1)

    print("transmit batch 2")
    server.transmit_batch(batch)

    time.sleep(1)
    
    c = 0
    while server.has_open_connections and c<30:
        c += 1
        print("Keep alive until disconnected")
        time.sleep(1)

if __name__ == "__main__":
    print()
    print("START batch server")
    print()
    c104.set_debug_mode(mode=c104.Debug.Server)
    main()