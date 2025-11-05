import functools
import time
import c104

c104.set_debug_mode(mode=c104.Debug.Client|c104.Debug.Connection)
print("CL] DEBUG MODE: {0}".format(c104.get_debug_mode()))

my_client = c104.Client(tick_rate_ms=1000, command_timeout_ms=5000)
my_client.originator_address = 123
cl_connection_1 = my_client.add_connection(ip="127.0.0.1", port=2404, init=c104.Init.NONE)


##################################
# CONNECTION STATE HANDLER
##################################

def cl_ct_on_state_change(connection: c104.Connection, state: c104.ConnectionState) -> None:
    print("CL] Connection State Changed {0} | State {1}".format(connection.originator_address, state))

    if state == c104.ConnectionState.OPEN_MUTED:
        for m in ("start_data_transfer", "send_startdt_act", "start_dt", "start"):
            if hasattr(connection, m):
                getattr(connection, m)()
                print("CL] -> STARTDT_ACT sent")
                break
    
    if state in (getattr(c104.ConnectionState, "OPEN", None),
                 getattr(c104.ConnectionState, "OPEN_UNMUTED", None)):
        try:
            ca = 1
            if not any(st.common_address == ca for st in connection.stations):
                connection.add_station(common_address=ca)
            st = next(st for st in connection.stations if st.common_address == ca)

            sent = False

            for m in ("general_interrogation", "interrogation", "send_general_interrogation", "gi"):
                if hasattr(st, m):
                    getattr(st, m)(qoi=getattr(c104, "QOI_GLOBAL", 20))
                    print(f"CL] -> GI sent to CA={ca}, QOI=20 (global)")
                    sent = True
                    break
            if not sent:
                for m in ("send_interrogation", "general_interrogation", "interrogation"):
                    if hasattr(connection, m):
                        getattr(connection, m)(common_address=ca, qoi=getattr(c104, "QOI_GLOBAL", 20))
                        print(f"CL] -> GI sent to CA={ca}, QOI=20 (global)")
                        break
        except Exception as e:
            print(f"GL] GI dispatch failed: {e}")



cl_connection_1.on_state_change(callable=cl_ct_on_state_change)

MEASURED_TYPES = {
    getattr(c104.Type, "M_ME_NA_1", None),  # normalized
    getattr(c104.Type, "M_ME_NB_1", None),  # scaled
    getattr(c104.Type, "M_ME_NC_1", None),  # short float (common)
    getattr(c104.Type, "M_ME_TF_1", None),  # time-tagged float (if supported)
}

# Map IOA -> signal name once you learn the device’s IOA map
IOA_NAMES = {
    30001: "U_L1 (V)",
    30002: "U_L2 (V)",
    30003: "U_L3 (V)",
    # ... fill in after your first GI
}

##################################
# NEW DATA HANDLER
##################################

def cl_pt_on_receive_point(point: c104.Point, previous_info: c104.Information, message: c104.IncomingMessage) -> c104.ResponseState:
    if point.type in MEASURED_TYPES:
        name = IOA_NAMES.get(point.io_address, f"IOA {point.io_address}")
        print(f"VOLTS] {name}: {point.value} @ {point.processed_at.isoformat()} q={point.quality}")
    else:
        print(f"CL] {point.type} REPORT on IOA {point.io_address}: {point.info}")
    return c104.ResponseState.SUCCESS


##################################
# NEW OBJECT HANDLER
##################################

def cl_on_new_station(client: c104.Client, connection: c104.Connection, common_address: int, custom_arg: str, y: str = "default value") -> None:
    print("CL] NEW STATION {0} | CLIENT OA {1}".format(common_address, client.originator_address))
    connection.add_station(common_address=common_address)


def cl_on_new_point(client: c104.Client, station: c104.Station, io_address: int, point_type: c104.Type) -> None:
    print("CL] NEW POINT: {1} with IOA {0} | CLIENT OA {2}".format(io_address, point_type, client.originator_address))
    point = station.add_point(io_address=io_address, type=point_type)
    point.on_receive(callable=cl_pt_on_receive_point)


my_client.on_new_station(callable=functools.partial(cl_on_new_station, custom_arg="extra argument with default/bounded value passes signature check"))
my_client.on_new_point(callable=cl_on_new_point)


##################################
# RAW MESSAGE HANDLER
##################################

def cl_ct_on_receive_raw(connection: c104.Connection, data: bytes) -> None:
    print("CL] <-in-- {1} [{0}] | CONN OA {2}".format(data.hex(), c104.explain_bytes_dict(apdu=data), connection.originator_address))


def cl_ct_on_send_raw(connection: c104.Connection, data: bytes) -> None:
    print("CL] -out-> {1} [{0}] | CONN OA {2}".format(data.hex(), c104.explain_bytes_dict(apdu=data), connection.originator_address))


cl_connection_1.on_receive_raw(callable=cl_ct_on_receive_raw)
cl_connection_1.on_send_raw(callable=cl_ct_on_send_raw)

##################################
# Dump points
##################################

def cl_dump():
    global my_client, cl_connection_1
    if cl_connection_1.is_connected:
        print("")
        cl_ct_count = len(my_client.connections)
        print("CL] |--+ CLIENT has {0} connections".format(cl_ct_count))
        for ct_iter in range(cl_ct_count):
            ct = my_client.connections[ct_iter]
            ct_st_count = len(ct.stations)
            print("       |--+ CONNECTION has {0} stations".format(ct_st_count))
            for st_iter in range(ct_st_count):
                st = ct.stations[st_iter]
                st_pt_count = len(st.points)
                print("          |--+ STATION {0} has {1} points".format(st.common_address, st_pt_count))
                print("             |      TYPE      |   IOA   |       VALUE        |        PROCESSED AT        |        RECORDED  AT        |      QUALITY      ")
                print("             |----------------|---------|--------------------|----------------------------|----------------------------|-------------------")
                for pt_iter in range(st_pt_count):
                    pt = st.points[pt_iter]
                    print("             | %s | %7s | %18s | %26s | %26s | %s" % (pt.type, pt.io_address, pt.value, pt.processed_at.isoformat(),
                                                                                 pt.recorded_at and pt.recorded_at.isoformat() or 'N. A.', pt.quality))
                    print("             |----------------|---------|--------------------|----------------------------|----------------------------|-------------------")


##################################
# connect loop
##################################

my_client.start()

while not cl_connection_1.is_connected:
    print("CL] Waiting for connection to {0}:{1}".format(cl_connection_1.ip, cl_connection_1.port))
    time.sleep(1)

##################################
# Loop through points
##################################

while cl_connection_1.is_connected:
    cl_dump()
    time.sleep(3)

##################################
# done
##################################

my_client.stop()