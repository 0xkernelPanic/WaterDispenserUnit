#!/usr/bin/python
import serial, csv, time, RPi.GPIO as io
from RPLCD import i2c

#LCD initialisation
i2c_lcd_mode = 'i2c'
i2c_lcd_cols = 20
i2c_lcd_rows = 4
i2c_lcd_charmap = 'A00'
i2c_lcd_address = 0x27
i2c_lcd_port = 1
i2c_lcd_expander = 'PCF8574'

i2c_lcd = i2c.CharLCD(i2c_lcd_expander, i2c_lcd_address, port=i2c_lcd_port, charmap=i2c_lcd_charmap, cols=i2c_lcd_cols, rows=i2c_lcd_rows)

#Serial initialisation
arduino = serial.Serial("/dev/ttyACM0")
arduino.timeout = 3

#CSV initialisation
csvfile = open("db.csv", newline="\n")
reader = csv.DictReader(csvfile)

#GPIO initialisation
in_btn_dispense = 11
in_btn_cancel = 13
in_btn_check_tds = 12
in_snr_flow = 33
#in_btn_restart = 14
out_led_red = 8
out_led_green = 10
out_bzr_notification = 38
out_sln_dispense = 40
out_sln_tdscheck = 37
out_avr_tdscheck = 35

io.setwarnings(False)
io.setmode(io.BOARD)

io.setup(in_btn_dispense, io.IN, pull_up_down=io.PUD_DOWN)
io.setup(in_btn_cancel, io.IN, pull_up_down=io.PUD_DOWN)
io.setup(in_btn_check_tds, io.IN, pull_up_down=io.PUD_DOWN)
io.setup(in_snr_flow, io.IN, pull_up_down=io.PUD_UP)
#io.setup(in_btn_restart, io.IN)

io.setup(out_led_red, io.OUT)
io.setup(out_led_green, io.OUT)

io.setup(out_bzr_notification, io.OUT)
io.setup(out_sln_dispense, io.OUT)
io.setup(out_sln_tdscheck, io.OUT)
io.setup(out_avr_tdscheck, io.OUT)

#
io.output(out_led_red, io.LOW)
io.output(out_led_green, io.LOW)

io.output(out_bzr_notification, io.LOW)
io.output(out_sln_dispense, io.LOW)
io.output(out_sln_tdscheck, io.LOW)
io.output(out_avr_tdscheck, io.LOW)

#Flow sensor initialisation

def signal_handler(sig,frame):
    gpio.cleanup()
    sys.exit(0)

def sensor_callback(chan):
    global counter
    counter+=1

io.add_event_detect(in_snr_flow,io.FALLING,callback=sensor_callback,bouncetime=1)

t_elapsed = 0.1 # time [s] between each flow rate calculation
counter = 0 # for counting and calculating frequency
Q_prev = 0.0 # previous flow calculation (for total flow calc.) [L/s]
conv_factor = 1.0/(7.5*60) # conversion factor to [L/s] from freq [1/s or Hz]
vol_approx = 0.0 # initial approximation of volume [L]
vol_prev   = 0.0 # for minimizing the prints to console

users = {"0007752813": ["Blue", 5],"0013987934": ["Yellow", 5]}

while True:
    print("LoopCycle_Debug")
    counter = 0
    vol_approx = 0
    i2c_lcd.clear()
    i2c_lcd.cursor_pos = (0,3)
    i2c_lcd.write_string("Water Dispenser")
    i2c_lcd.cursor_pos = (1,3)
    i2c_lcd.write_string("Tap to begin")
    io.output(out_led_red, 0)
    io.output(out_led_green, 0)
    io.output(out_sln_dispense, 1)
    io.output(out_sln_tdscheck, 1)
    
    val_btn_check_tds = io.input(in_btn_check_tds)

    if val_btn_check_tds == 1:
        io.output(out_sln_tdscheck, 1)
        io.output(out_avr_tdscheck, 1)
        i2c_lcd.cursor_pos = (0,3)
        i2c_lcd.write_string(arduino.readline())
        
    user_id = input("RFID: ")

    print("UserValid_Debug")
    i2c_lcd.clear()
    lcd_output = users[str(user_id)][0] + " has " + str(users[str(user_id)][1]) + " liters remaining. Select option."
    arduino.write(bytes(lcd_output, "utf-8"))
    i2c_lcd.cursor_pos = (1, 0)
    i2c_lcd.write_string(lcd_output)

    val_btn_dispense = io.input(in_btn_dispense)
    val_btn_cancel = io.input(in_btn_cancel)
    val_btn_check_tds = io.input(in_btn_check_tds)

    while val_btn_dispense == 0 and val_btn_cancel == 0 and val_btn_check_tds == 0:
        val_btn_dispense = io.input(in_btn_dispense)
        val_btn_cancel = io.input(in_btn_cancel)
        val_btn_check_tds = io.input(in_btn_check_tds)
    
    if val_btn_dispense == 1:
        if users[str(user_id)][1] < 1:
            i2c_lcd.clear()
            i2c_lcd.cursor_pos = (0, 3)
            i2c_lcd.write_string("Insufficient Ltrs")
            time.sleep(2)
            continue

        #print("ButtonPress_Debug")
        counter = 0
        #print("1")
        i2c_lcd.clear()
        i2c_lcd.cursor_pos = (0,3)
        #print("2")
        i2c_lcd.write_string("Dispensing...")
        #print("3")
        io.output(out_led_green, 1)
        #print("4")
        io.output(out_sln_dispense, 0)
        #print("5")
        counter = 0
        vol_approx = 0

        while vol_approx < 100:
            #print("6")
            Q = (conv_factor*(counter/t_elapsed)) # conversion to [Hz] then to [L/s]
            currentvolume=(t_elapsed*((Q+Q_prev)/2.0))*1000
            vol_approx+=int(currentvolume) # integrate over time for [L]
            counter = 0 # reset counter
            t0 = time.time() # get new time
            Q_prev = float(Q) # set previous rate
            print(vol_approx)
        
        counter = 0

        io.output(out_led_green, 0)
        io.output(out_sln_dispense, 1)
        i2c_lcd.clear()
        i2c_lcd.write_string("1L was subtracted.")
        users[str(user_id)][1] -= 1
        time.sleep(2)
        continue

        

    elif val_btn_cancel == 1:
        continue

    elif val_btn_check_tds == 1:
        if users[str(user_id)][0] != "Yellow":
            i2c_lcd.clear()
            i2c_lcd.cursor_pos = (0, 3)
            i2c_lcd.write_string("Access Denied")
            time.sleep(2)
            continue

        print("TDSSENSOR_Debug")
        time.sleep(1)
        for i in range(1, 120):
            val_btn_cancel = io.input(in_btn_cancel)
            if val_btn_cancel == 1:
                break
            val_btn_check_tds = io.input(in_btn_check_tds)
            io.output(out_sln_tdscheck, False)
            i2c_lcd.clear()
            i2c_lcd.cursor_pos=(0,4)
            tdsdata = arduino.readline().decode('utf-8').rstrip()
            i2c_lcd.write_string('TDS Value')
            i2c_lcd.cursor_pos=(1,3)
            i2c_lcd.write_string(tdsdata)
            i2c_lcd.cursor_pos=(1,7)
            i2c_lcd.write_string('ppm')
            print(tdsdata)
            time.sleep(0.5)
        io.output(out_sln_tdscheck, True)
        continue
        if int(tdsdata) > 300:
            io.output(out_led_red, True)
            #io.output(buzzer,True)
            time.sleep(2)
            continue
    
    else:
        print("UserInvalid_Debug")
        #pass #arduino.write(bytes("User Unknown", "utf-8"))

    




