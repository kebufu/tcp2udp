import socket,binascii,select,struct,sys

remote=('',4455)
local=('0.0.0.0',21)

connections={}

s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
server=socket.socket()
server.bind(local)
server.listen()

def recvPacket():
    packet,_=s.recvfrom(1464)
    crc32=struct.unpack(">I",packet[0:4])[0]
    packet=packet[4:]
    if crc32!=binascii.crc32(packet):
        return
    else:
        return packet

def sendPacket(data,addr):
    assert len(data)<1460,"Packet more than 1460 bytes."
    buffer=struct.pack(">I",binascii.crc32(data))+data
    s.sendto(buffer,addr)
    while 0:
        r,_,_=select.select([s],[],[],2)
        if r:
            data=recvPacket()
            if data[0]==0:
                s.sendto(b'\xd2\x02\xef\x8d\x00',addr)
                return
        s.sendto(buffer,addr)

def printError(err):
    print("="*5+"Internal Server Error"+"="*5,file=sys.stderr)
    print(err)
    print("="*len("="*5+"Internal Server Error"+"="*5),file=sys.stderr)

def getKey(dict,value):
    for k,v in dict.items():
        if v==value:
            return k
    return None

while 1:
    r,w,e=select.select([s,server]+list(connections.values()),list(connections.values()),list(connections.values()),0)
    for i in r:
        if i==s:
            packet=recvPacket()
            if not packet:
                continue
            #s.sendto(b'\xd2\x02\xef\x8d\x00',remote)
            action=packet[0]
            payload=packet[1:]
            if action==3:
                id=struct.unpack(">I",payload[:4])
                if connections.get(id):
                    connections[id].shutdown(socket.SHUT_RDWR)
                    del connections[id]
                    if payload[4:]:
                        printError(payload[4:].decode("utf-8"))
            elif action==2:
                id=struct.unpack(">I",payload[:4])
                if connections.get(id):
                    connections[id].sendall(payload[4:])
            elif action==1:
                pass
            elif action==0xFE:
                print(f"error:{payload.decode('utf-8')}")
            else:
                pass
            continue
        elif i==server:
            user,addr=server.accept()
            sendPacket(b"\x00",remote)
            recvPacket()
            packet=recvPacket()
            if packet[0]==0xFE:
                user.shutdown(socket.SHUT_RDWR)
                print(f"error:{packet[1:].decode('utf-8')}")
            else:
                print(packet[0])
                id=struct.unpack(">I",packet[1:5])
                connections[id]=user
            continue
        id=getKey(connections,i)
        try:
            data=i.recv(1455)
            if data:
                sendPacket(b"\x01"+struct.pack(">I",id[0])+data,remote)
            else:
                i.shutdown(socket.SHUT_RDWR)
                sendPacket(b"\x02"+struct.pack(">I",id),remote)
                del connections[id]
        except:
            sendPacket(b"\x02"+struct.pack(">I",id[0]),remote)
            del connections[id]
