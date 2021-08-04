# -*- coding: utf-8 -*-

from ucsmsdk.ucshandle import UcsHandle
import json

"""
Cisco UCS Fabric Interconnects Management Class
"""
class Ucsmanger():
    def __init__(self, ip, user, pwd):
        self.ip = ip
        self.user = user
        self.pwd = pwd
        self.handle = None
    
    def login(self):
        try:
            self.handle = UcsHandle(self.ip, self.user, self.pwd)
            self.handle.login()
            return True
        except:
            print ("login fail: {}".format(self.ip))
            self.handle = None
            return False
    
    def logout(self):
        self.handle.logout()
        self.handle = None
    
    def query_classid(self, class_id, filter_str=None):
        return self.handle.query_classid(class_id=class_id, filter_str=filter_str)
    
    def query_dn(self, dn):
        return self.handle.query_dn(dn=dn)

    # Blade + RackUnit
    def list_servers(self):
        from ucsmsdk.mometa.compute.ComputeRackUnit import ComputeRackUnit
        from ucsmsdk.mometa.compute.ComputeBlade import ComputeBlade

        blades = self.handle.query_classid(class_id="ComputeBlade")
        servers = self.handle.query_classid(class_id="ComputeRackUnit")
        sub_data = self.handle.query_classid(class_id="lsServer")
        
        all_list = blades + servers
        all_servers = []
        for s in all_list:
            data = {
                    'dn': s.dn,
                    'id':s.id,
                    'service_profile': s.assigned_to_dn,
                    'power': s.oper_power,
                    'oper_state': s.oper_state,
                    'admin': s.admin_state,
                    'discovery': s.discovery,
                    'avail': s.availability,
                    'assoc': s.association,
                    'slot': s.presence,
                    'checkpoint': s.check_point,
                    'vendor': s.vendor,
                    'pid': s.model,
                    'revision': s.revision,
                    'serial': s.serial,
                    'assettag': s.asset_tag,
                    'name': s.name,
                    'usr_lbl': s.usr_lbl,
                    'uuid': s.uuid,
                    'original_uuid': s.original_uuid,
                    'num_cpu': s.num_of_cpus,
                    'num_cores_enabled': s.num_of_cores_enabled,
                    'num_cores': s.num_of_cores,
                    'num_threads': s.num_of_threads,
                    'available_memory': s.available_memory,
                    'total_memory': s.total_memory,
                    'memory_speed': s.memory_speed,
                    'low_voltage_memory': s.low_voltage_memory,
                    'adaptors': s.num_of_adaptors,
                    'nics': s.num_of_eth_host_ifs,
                    'hbas': s.num_of_fc_host_ifs,
                    'conn_path': s.conn_path,
                    'conn_status': s.conn_status,
                    'managing_inst': s.managing_inst,
                    'descr': s.descr,
                    'ipaddress': '',
                    'subnet': '',
                    'gateway': ''
                    }
            if type(s) is ComputeBlade:
                data['type'] = "blade"
                data['chassis_id'] = s.chassis_id
                data['slot'] = s.rn.replace("blade-", "")
            if type(s) is ComputeRackUnit:
                data['type'] = "rack"
                data['rack_id'] = s.rn.replace("rack-unit-", "")
                
            for sub_s in sub_data:
                if sub_s.assign_state == 'assigned' and sub_s.pn_dn == s.dn:
                    data['usr_lbl'] = sub_s.usr_lbl
                    break
    
            all_servers.append(data)
        return all_servers
    
    # Get IPAddress, Subnet, Gateway Info
    def get_IPaddress(self, server_data):
        eth = self.handle.query_classid(class_id="ippoolPooled")
        for e in eth:
            if server_data['dn'] in e.assigned_to_dn:
                server_data["ipaddress"] = e.id
                server_data["subnet"] = e.subnet
                server_data["gateway"] = e.def_gw
                break
        
    # Get Fault Data
    def get_Fault(self, server_data):
        fault = self.handle.query_classid(class_id="faultInst")
        fault_list = []
        
        for f in fault:
            if server_data['dn'] in f.dn:
                fault_list.append({
                    'code': f.code,
                    'severity': str(f.severity).lower(),
                    'orig_severity': str(f.orig_severity).lower(),
                    'prev_severity': str(f.prev_severity).lower(),
                    'highest_severity': str(f.highest_severity).lower(),
                    'occur': f.occur,
                    'created': f.created,
                    'last_transition': f.last_transition,
                    'descr': f.descr,
                    'id': f.id,
                    'cause': f.cause,
                    'dn': str(f.dn)[:str(f.dn).rfind('/')],
                    'type': f.type
                    })

        server_data['critical'] = len(filter(lambda a :a['severity'] =='critical', fault_list))
        server_data['major'] = len(filter(lambda a :a['severity'] =='major', fault_list))
        server_data['minor'] = len(filter(lambda a :a['severity'] =='minor', fault_list))
        server_data['warning'] = len(filter(lambda a :a['severity'] =='warning', fault_list))
        server_data['fault_list'] = fault_list
    
    # Get Temperature info by board, cpu, memory
    def get_temperature(self, rackdn):
        board_list = self.handle.query_classid(class_id="computeMbTempStats")
        cpu_list = self.handle.query_classid(class_id="processorUnit")
        memory_list = self.handle.query_classid(class_id="memoryUnit")
        
        all_temperature = {
                'motherboard':[],
                'cpus':[],
                'memorys':[]
                }
        
        for b in board_list:
            if rackdn in b.dn:
                data = {
                        'dn': b.dn,
                        'value': b.fm_temp_sen_io,
                        'avg': b.fm_temp_sen_io_avg,
                        'min': b.fm_temp_sen_io_min,
                        'max': b.fm_temp_sen_io_max
                        }
                all_temperature['motherboard'].append(data)
                
        for c in cpu_list:
            if rackdn in c.dn and c.oper_state == 'operable':
                dn = "{}/env-stats".format(c.dn)
                env = self.handle.query_dn(dn=dn)
                data = {
                        'id': c.id,
                        'socket_designation': c.socket_designation,
                        'value': env.temperature,
                        'avg': env.temperature_avg,
                        'min': env.temperature_min,
                        'max': env.temperature_max
                        }
                all_temperature['cpus'].append(data)
        
        for m in memory_list:
            if rackdn in m.dn and m.oper_state == 'operable':
                dn = "{}/dimm-env-stats".format(m.dn)
                env = self.handle.query_dn(dn=dn)
                data = {
                        'id': m.id,
                        'location': m.location,
                        'value': env.temperature,
                        'avg': env.temperature_avg,
                        'min': env.temperature_min,
                        'max': env.temperature_max
                        }
                all_temperature['memorys'].append(data)
                
        return all_temperature
    
    # Get Power info
    def get_power(self, rackdn):
        power = self.handle.query_classid(class_id="computeMbPowerStats")
        all_power = []
        for p in power:
            if rackdn in p.dn:
                data = {
                        'value': p.consumed_power,
                        'avg': p.consumed_power_avg,
                        'min': p.consumed_power_min,
                        'max': p.consumed_power_max
                        }
                all_power.append(data)
        return all_power
    
    # Get StorageLocalDisk
    def get_storageLocalDisk(self, rackdn):
        storage_list = self.handle.query_classid(class_id="storageLocalDisk")
        all_storage = []
        for s in storage_list:
            if rackdn in s.dn:
                data = {
                        'dn': s.dn,
                        'id': s.id,
                        'vendor': s.vendor,
                        'serial': s.serial,
                        'revision': s.revision,
                        'variant': s.variant_type,
                        'disk_state': s.disk_state,
                        'power_state': s.power_state,
                        'size': s.size,
                        'link_speed': s.link_speed,
                        'number_of_blocks': s.number_of_blocks,
                        'block_size': s.block_size,
                        'physical_block_size': s.physical_block_size,
                        'technology': s.device_type,
                        'oper_qualifier_reason': s.oper_qualifier_reason,
                        'operability': s.operability,
                        'presence': s.presence
                        }
                all_storage.append(data)
        
        return all_storage

def main():
    ip = "10.10.10.10"
    user = "admin"
    pwd = "admin"

    ucsfi_obj = Ucsmanger(ip, user, pwd)
    if ucsfi_obj.login() == False:
        return

    try:
        ucslist = ucsfi_obj.list_servers()

        for ucs in ucslist:
            print (ucsfi_obj.get_storageLocalDisk(ucs['dn']))
            print (ucsfi_obj.get_power(ucs['dn']))
            print (ucsfi_obj.get_temperature(ucs['dn']))
            ucsfi_obj.get_IPaddress(ucs)
            ucsfi_obj.get_Fault(ucs)

        print (ucs)
    except Exception as e:
        print ("Fail!! error msg : {}".format(e))
    finally:
        ucsfi_obj.logout()

# Start program
if __name__ == "__main__":
    main()
