class ServiceCodes:
    CIP_SERVICE_CODES = {
        0x01: "Get_Attribute_All",
        0x02: "Set_Attribute_All",
        0x03: "Get_Attribute_List",
        0x04: "Set_Attribute_List",
        0x05: "Reset",
        0x06: "Start",
        0x07: "Stop",
        0x08: "Create",
        0x09: "Delete",
        0x0a: "Multiple_Service_Packet",
        0x0d: "Apply_attributes",
        0x0e: "Get_Attribute_Single",
        0x10: "Set_Attribute_Single",
        0x4b: "Execute_PCCC_Service",  # PCCC = Programmable Controller Communication Commands
        0x4c: "Read_Tag_Service",
        0x4d: "Write_Tag_Service",
        0x4e: "Read_Modify_Write_Tag_Service",
        0x4f: "Read_Other_Tag_Service",  # ???
        0x52: "Read_Tag_Fragmented_Service",
        0x53: "Write_Tag_Fragmented_Service",
        0x54: "Forward_Open?",
        0xcc: "Read Tag Response",
        0xd2: "Read Tag Fragmented Response",
        0xcd: "Write Tag Response",
        0xd3: "Write Tag Fragmented Response",
        0xce: "Read Modify Write Tag Response",
        0x8a: "Multiple Service Packet Response",
        0xd5: "Get Instance Attributes List Response",
        0x83: "Get Attributes Response",
    }

    MODBUS_SERVICE_CODES = {}
