from serial import Serial
from tqdm import tqdm
import time
import types
import random
import os

def int16Bytes(int16: int) -> bytes:
    return int16.to_bytes(2, "big")

def readEEPROM(serial: Serial, address: int) -> bytes:
    serial.reset_input_buffer()
    serial.write(b"r" + int16Bytes(address))
    return serial.read()

def writeEEPROM(serial: Serial, address: int, data: int):
    serial.write(b"w" + int16Bytes(address) + data.to_bytes(1, "big"))

    while serial.in_waiting == 0:  # wait for okay byte
        continue

    serial.read() # clean up okay byte

debugFill = []

def loadEEPROM(serial: Serial, startAddress: int, data: bytes, callback: types.FunctionType = None):
    global debugFill
    
    serial.reset_input_buffer()

    targetFill = 16 # target number of bytes to be filled in the arduino's buffer
    count = len(data)
    offset = 0
    readCount = 0

    command = b"l" + int16Bytes(startAddress) + int16Bytes(count)
    serial.write(command)
    iterations = targetFill
    fill = targetFill

    while offset < count:
        if iterations > count - offset:  # cap iterations to prevent over-iterating
            iterations = count - offset

        for i in range(iterations):
            serial.write(data[offset])
            offset += 1

        waitingCount = serial.in_waiting

        if waitingCount > 0:
            readCount += waitingCount
            serial.read(waitingCount)

        if callback is not None:
            callback(waitingCount)

        # assume all sent bytes are not processed and end up in arduino's buffer
        # fill = sendBytes - writtenBytes
        fill = offset - readCount
        print(fill)

        # perform the number of iterations necessary to fill the arduino's buffer to target fill
        iterations = targetFill - fill

    while serial.in_waiting != count - readCount: # wait for last writes to okay
        continue

    if callback is not None:
        callback(serial.in_waiting) # final bytes

    serial.reset_input_buffer()

def dumpEEPROM(serial: Serial, startAddress: int, count: int, callback: types.FunctionType = None) -> bytes:
    data = bytearray(count)
    index = 0
    serial.write(b"d" + int16Bytes(startAddress) + int16Bytes(count))

    while index < count:
        readBytes = serial.read()[0]
        if callback is not None:
            callback(1)
        data[index] = readBytes
        index += 1

    return data

def writeFileEEPROM(filePath: str, serial: Serial):
    data = []

    # 1 byte file name length
    # n bytes file name
    # 2 byte file length
    # n bytes file

    fileName = os.path.basename(filePath)
    print(fileName)

    fileNameBytes = bytes(fileName, 'utf-8')
    print(fileNameBytes)
    print(len(fileNameBytes).to_bytes(1, "big"))

    data.append(len(fileNameBytes).to_bytes(1, "big"))
    data.append(fileNameBytes)

    with open(filePath, "rb") as f:
        binData = f.read()
        data.append(len(binData).to_bytes(2, "big"))
        
        for b in binData:
            data.append(b.to_bytes(1, "big"))

    loadEEPROM(serial, 0, data)

def readFileEEPROM(fileDirectory: str, serial: Serial):
    fileNameLength = int.from_bytes(readEEPROM(serial, 0), "big")
    fileNameBytes = dumpEEPROM(serial, 1, fileNameLength)
    fileName = fileNameBytes.decode("utf-8")

    fileLength = int.from_bytes(dumpEEPROM(serial, 1 + fileNameLength, 2), "big")
    fileData = dumpEEPROM(serial, 1 + fileNameLength + 2, fileLength)

    print(f"File name length: {fileNameLength}")
    print(f"File name: {fileName}")

    print(f"File length: {fileLength}")

    print(os.path.join(fileDirectory, fileName))

    with open(os.path.join(fileDirectory, fileName), "wb") as f:
        f.write(fileData)

def tqdmDataBar(desc: str, total: int):
    return tqdm(desc=desc, total=total, unit="b", unit_scale=True, unit_divisor=1024)

def testEEPROM(serial: Serial):
    data = []

    for i in range(32768):
        r = random.randrange(256)
        data.append(r.to_bytes(1, "big"))

    t = tqdmDataBar("Load", len(data))
    loadEEPROM(serial, 0, data, t.update)
    t.close()

    t = tqdmDataBar("Dump", len(data))
    dataDump = dumpEEPROM(serial, 0, len(data), t.update)
    t.close()

    for i in range(len(data)):
        readByte = dataDump[i]
        expectedByte = data[i]

        expectedInt = int.from_bytes(expectedByte, "big")

        if readByte != expectedInt:
            continue
            print(
                f"Read {readByte} but expected {expectedInt} at address {i.to_bytes(2, 'big').hex()}"
            )

    print("Done!")

def main():
    global debugFill

    serial = Serial("COM6", 115200, timeout=0.1)
    time.sleep(2)

    serial.reset_input_buffer()
    serial.reset_output_buffer()

    testEEPROM(serial)
    serial.close()
    return

    #writeEEPROM(serial, 0, 0x0D)
    
    with open("dump.bin", "wb") as f:
        f.write(dumpEEPROM(serial, 0, 32768))
    

    #writeFileEEPROM("cutemouse.jpg", serial)
    #readFileEEPROM("./", serial)

    return

    data = []
    startAddr = 0

    # for i in range(32768):
    #     r = random.randrange(256)
    #     data.append(r.to_bytes(1, "big"))

    with open("cat.jpg", "rb") as f:
        binData = f.read()

        for b in binData:
            data.append(b.to_bytes(1, "big"))

    print(f"Data length: {len(data)}")

    t = tqdmDataBar("Load", len(data))
    loadEEPROM(serial, startAddr, data, t.update)
    t.close()

    t = tqdmDataBar("Dump", len(data))
    dataDump = dumpEEPROM(serial, startAddr, len(data), t.update)
    t.close()

    print(debugFill)

    f = open("output.jpg", "wb")
    f.write(dataDump)
    f.close()

    # return

    for j in range(len(data)):
        i = j + startAddr
        readByte = dataDump[j]
        expectedByte = data[j]

        expectedInt = int.from_bytes(expectedByte, "big")

        #print(i, end="\t")
        if readByte != expectedInt:
            continue
            print(
                f"Read {readByte} but expected {expectedInt} at address {i.to_bytes(2, 'big').hex()}"
            )

    print("Done!")

    serial.close()

if __name__ == "__main__":
    main()