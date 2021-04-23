import socket,binascii,select,struct,random,traceback,time,sys

connections={}
mappings={}

remote=('127.0.0.1',1080)
local=("0.0.0.0",1433)

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(local)

'''
Packets:
    crc32(4 bytes unsiged little endian) action(1 byte unsiged little endian) payload
'''

def recvPacket():
    packet,_=server.recvfrom(1464)
    crc32=struct.unpack(">I",packet[0:4])[0]
    packet=packet[4:]
    if crc32!=binascii.crc32(packet):
        return
    else:
        return packet

def sendPacket(data,addr):
    assert len(data)<1460,"Packet more than 1460 bytes."
    buffer=struct.pack(">I",binascii.crc32(data))+data
    server.sendto(buffer,addr)
    while 0:
        r,_,_=select.select([server],[],[],2)
        if r:
            data=recvPacket()
            if data[0]==0:
                server.sendto(b'\xd2\x02\xef\x8d\x00',addr)
                return
        server.sendto(buffer,addr)

def randomConnectionId():
    if len(connections)>=2**32-1:
        return None
    rnd=random.randint(0,2**32-1)
    while connections.get(rnd)!=None:
        rnd=random.randint(0,2**32-1)
    return rnd

def printError():
    print("="*5+"Internal Server Error"+"="*5,file=sys.stderr)
    traceback.print_exc()
    print("="*len("="*5+"Internal Server Error"+"="*5),file=sys.stderr)

def getKey(dict,value):
    for k,v in dict.items():
        if v==value:
            return k
    return None

while 1:
    readable,writeable,errors=select.select([server]+list(connections.values()),connections.values(),connections.values(),0)
    for i in readable:
        if i==server:
            packet,address=server.recvfrom(1464)
            if len(packet)<4:
                continue
            crc32=struct.unpack(">I",packet[0:4])[0]
            packet=packet[4:]
            if crc32!=binascii.crc32(packet):
                sendPacket(b"\xff"+struct.pack(">I",crc32)+struct.pack(">I",binascii.crc32(packet)),address)
                continue
            sendPacket(b"\x00",address)
            action=packet[0]
            payload=packet[1:]
            ts=time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
            if action==0:
                connectionId=randomConnectionId()
                if connectionId==None:
                    sendPacket(b"\xFENo avalible connections",address) #No avalible connections.
                    continue
                try:
                    s=socket.socket()
                    s.connect(remote)
                    connections[connectionId]=s
                    mappings[connectionId]=address
                    sendPacket(b"\x01"+struct.pack(">I",connectionId),address)
                    print(f"{ts} {address[0]}:{address[1]} connected.")
                except:
                    sendPacket(b"\xFE"+traceback.format_exc().encode("utf-8"),address)
                    printError()
            elif action==1:
                connectionId=struct.unpack(">I",payload[0:4])[0]
                if connections.get(connectionId)==None:
                    sendPacket(b"\xFENo such connection",address)
                    continue
                try:
                    connections[connectionId].sendall(payload[4:])
                except:
                    sendPacket(b"\xFE"+traceback.format_exc().encode("utf-8"),address)
                    printError()
            elif action==2:
                connectionId=struct.unpack(">I",payload[:4])[0]
                if connections.get(connectionId)==None:
                    sendPacket(b"\xFENo such connection",address)
                    continue
                try:
                    connections[connectionId].shutdown(socket.SHUT_RDWR)
                    del connections[connectionId]
                    del mappings[connectionId]
                except:
                    sendPacket(b"\xFE"+traceback.format_exc().encode("utf-8"),address)
                    printError()
            else:
                sendPacket("\xFEUnknown action type.",address)
            continue
        connectionId=getKey(connections,i)
        if connectionId==None or mappings.get(connectionId)==None:
            i.shutdown(socket.SHUT_RDWR)
            if mappings.get(connectionId):
                del mappings[connectionId]
            continue
        try:
            data=i.recv(1455)
            if data:
                sendPacket(b"\x02"+struct.pack(">I",connectionId)+data,mappings[connectionId])
            else:
                i.shutdown(socket.SHUT_RDWR)
                sendPacket(b"\x03"+struct.pack(">I",connectionId),mappings[connectionId])
                del connections[connectionId]
                del mappings[connectionId]
        except:
            sendPacket(b"\x03"+struct.pack(">I",connectionId)+traceback.format_exc().encode("utf-8"),mappings[connectionId])
            del connections[connectionId]
            del mappings[connectionId]
    for i in errors:
        pass
