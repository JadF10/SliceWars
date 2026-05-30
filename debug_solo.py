import socket
import json

HOST = '127.0.0.1'
PORT = 5555
s = socket.socket()
s.connect((HOST, PORT))

def send(msg):
    s.sendall((json.dumps(msg) + '\n').encode())

def recv():
    data = b''
    while b'\n' not in data:
        data += s.recv(4096)
    return json.loads(data.split(b'\n')[0])

send({'type':'CONNECT','server_time':0,'payload':{'username':'TestSolo'}})
print('CONNECT sent')
print('Response:', recv())

send({'type':'SOLO_START','server_time':0,'payload':{}})
print('SOLO_START sent')

for i in range(5):
    try:
        s.settimeout(3)
        msg = recv()
        print('Message', i+1, msg.get('type'), len(msg.get('payload',{}).get('items',[])))
    except:
        print('Message', i+1, 'timeout')
        break

s.close()
print('Done')
