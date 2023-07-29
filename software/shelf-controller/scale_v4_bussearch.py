import serial
import time
import re

min = 0x0
max = 0xffff_ffff_ffff

def send_and_recv(str_to_send, echo_out = False, print_return = False):
    if echo_out:
        print(f"<<{str_to_send}")
    ser.write(str_to_send.encode() + b'\n')

    out = ser.readline().decode().strip()
    if out != '' and print_return:
        print (f">>{out}")

    # analyse output
    # Define the regular expression pattern to capture the relevant parts
    pattern = r'^([rw])\s+((?:[A-Fa-f0-9]{2}\s+){1,})$'

    # Use the regular expression to match the input string
    match = re.match(pattern, out+"\n")

    ret_val = []
    if match:
        # Extract the captured groups
        command = match.group(1)     # 'r' or 'w'
        hex_numbers = match.group(2).split()   # Split numbers separated by spaces

        # Convert numbers to integers (base 16) and print the results
        #print(f"Command: {command}")
        #print("Hex Numbers:")
        for number in hex_numbers:
            decimal_number = int(number, 16)
            ret_val = ret_val + [decimal_number]
            #print(decimal_number)
    else:
        print(f"Invalid data from serial: {out}")

    return (command, ret_val)


def bin_search():
    l = min
    r = max
    i = 0
    while i<52:
        m = l + (r-l)//2

        #print(f"i: {i} {l:014_X} {m:014_X} {r:014_X}")
        str_to_send = f"w0003{m:#013X}".replace("X","")
        #print(str_to_send)
        send_and_recv(str_to_send)

        str_to_send = f"r0801"
        #print(str_to_send)

        res = send_and_recv(str_to_send)
        #print(res)

        if res[1][1] == 0x00:
            if r-l<=1: return m #Ausgabe, falls 0 gesucht wurde
            r = m
        else:
            if r-l<=1: return r #Ausgabe aller anderen Adressen
            l = m+1

        i+=1

    return False #nichts gefunden. Waage während des Suchlaufs kaputtgegangen?


ser = serial.Serial(
    port='/dev/cu.usbserial-AE01DTXS',
    baudrate=115200,
    timeout=1,
)
ser.isOpen()

# Waagen Neustart
send_and_recv("w0000")
print("Warte auf Waagen, bis sie den Neustart ausgeführt haben. 8 Sekunden ...")
time.sleep(8)

#alle LEDs an
send_and_recv("w0005")
time.sleep(0.9)
#Antwort bit setzen
send_and_recv("w0001")
time.sleep(.1)
#alle LEDs aus
send_and_recv("w0004")
time.sleep(.1)

anzahl_waagen = 0
weiter_suchen = True
while weiter_suchen:
    #test, ob noch waagen ohne neue I2C Adresse
    print(f"Suche nach weiteren Waage. ", end="")
    m = 0xffff_ffff_ffff
    str_to_send = f"w0003{m:#013X}".replace("X","")
    send_and_recv(str_to_send)

    str_to_send = f"r0801"
    res = send_and_recv(str_to_send)
    print(f"Rückgabewerte der Suche: {res}")

    weiter_suchen = True if res[1][0] > 0 else False

    if weiter_suchen: #welche haben sich gemeldet
        anzahl_waagen += 1
        neue_i2c_adresse = anzahl_waagen + 8 #ab Adresse 9 geht's los

        res2 = bin_search()
        print(f"Waage mit MAC {res2:014_X} gefunden.")

        print(f"Setze Wagge (Suchlauf {anzahl_waagen}): {res2:014_X} auf I2C Adresse {neue_i2c_adresse:02X}")
        res2 = send_and_recv(f"w0002{res2:012X}{neue_i2c_adresse:02X}")
        print(f"Rückgabewert Schreiben I2C Adresse: {res2}")
        time.sleep(0.5)
        #individuelle LED an
        send_and_recv(f"w{neue_i2c_adresse:02X}03")
        time.sleep(0.1)

print(f"gefundene Waagen Anzahl: {anzahl_waagen}")


ser.close()