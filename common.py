#transfer.py
#a module providing file transfer routines for both client and server
import easyaes, time, hashlib, os, thread
from math import ceil as __ceil__

class _globals():
        pass

class WatcherSock():
    """A wrapper class for socket that receives from watchersockbuffer instead of the actual socket"""
    def __init__(self,sock):
        self.sock = sock
        
    def recv(self,n):
        message = ""
        while len(message) < n:
            if g.watchersockbuffer:
                message += g.watchersockbuffer.pop(0)
        return message

    def send(self,message):
        self.sock.send(message)

def sha(x):
        return hashlib.sha512(x).digest()

def ceil(x,y):
    """ Returns x/y rounded up to the nearest integer """
    return int(__ceil__(float(x)/y))

def makeheader(first,*args):
    """
    first should be an int in the range 0 <= first <= 255
    Any following arguments can be anything, and will be placed in consecutive header fields.
    """
    header = chr(first) + chr(0)*bool(args)
    for arg in args:
        if type(arg) == str:
            header += arg + chr(0)
        elif type(arg) == int or type(arg) == float:
            header += str(arg) + chr(0)
        else:
            raise Exception("Unsupported type (can only send strings, ints and floats")
    header += chr(255) #i'd really prefer to use something like : and | as delimiters, but since there doesn't seem to be a single character that doesn't appear in file paths on any system, I'm using non-printable characters
    return header

def request_send(path=None,exactsize=None):
    if not exactsize:
        print path
        length = ceil(os.stat(path).st_size,16)*16 + 256 #now length is a generous estimate of ciphertext filesize
        message = makeheader(3,length)
        socket.send(message) #send request has no body
    else:
        socket.send(makeheader(3,exactsize))
    reply = socket.recv(1)
    if ord(reply) != 1:
        print "Upload request denied. Sorry."
        return False
    return True

def upload(data):
    """ Sends a large string data to the server, using sha to ensure integrity """ 
    cursor = 0
    while cursor < len(data):
        if len(data) - cursor >= 256:
            block = data[cursor:cursor+256]
        else:
            block = data[cursor:]
        socket.send(block)
        socket.send(sha(block))
        cursor += 256

    #wait for acknowledgement from server
    resend = ""
    while True:
        resend += socket.recv(1)
        if resend[-1] == chr(255):
            print resend
            resend = [int(i) for i in resend.split(chr(0))[:-1]]
            break
    print "resend =", resend
    for i in resend:
        #resend corrupted blocks
        print "resending block", i
        socket.send(
            makeheader(4, min(256,len(data)-i))
            )
        upload(data[ i : min(i+256,len(data)) ])
    return len(resend)

def download(sock,exactsize):
    """ Receives a file, checking a hash after every 256 bytes """
    print "download running from common's namespace"
    exactsize = int(exactsize)
    bytesreceived = 0
    resend = []
    bytestream = ""
    time.sleep(1)
    while bytesreceived < exactsize:
        block = sock.recv(min(exactsize-bytesreceived-64,256))
        HASH = sock.recv(64)
        #print "got block", len(block), len(HASH)
        #check block
        if sha(block) != HASH:
            #add a resend request
            print "hash doesn't match"
            resend.append(bytesreceived - 64*bytesreceived / 320) #working out where the corrupted block started in the original data (without hashes)
        bytestream += block #don't worry, we'll request a resend and overwrite it if it was corrupted
        bytesreceived += 256+64
    print len(resend), "out of", ceil(exactsize,256), "blocks corrupted"
    message = ""
    for i in resend: #i for index (in the original, unhashed bytestream back on clientside)
        raise
        message += str(i) + chr(0)
    message += chr(255)
    sock.send(message)
    print "sent acknowledgement:", message
    for i in resend:
        #now receive the resends, if any
        print "getting resend", i
        exactsize = receive_header(sock)[1][0]
        block = download(sock,exactsize)
        print "got resend"
        #now insert the correct block back into the bytestream, overwriting the corrupted block
        bytestream = bytestream[:i]+block+bytestream[i+256:]
    return bytestream

g = _globals()
g.watchersockbuffer = []
