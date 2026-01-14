import csv
import requests

from pathlib import Path
from time import perf_counter, sleep, time, localtime, strftime
from temp import temp
from helpers import helpers

csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?output=csv"
local_csv_path = Path("cached_google_sheet.csv")
step=5 #minutos de pause entre step
room_temp=15 #celsius
T=temp()
H=helpers()
IPS=[]
HYPER=[]

#máxima temperatura a la que deberia estar cualquier resistencia
max_temp=100

# Tasmota controllers
def on(HOST):
    requests.get(f"http://{HOST}/cm?cmnd=Power On")

def off(HOST):
    requests.get(f"http://{HOST}/cm?cmnd=Power Off")

def state(HOST):
    r = requests.get(f"http://{HOST}/cm?cmnd=Power")
    print(r.text)


# Usage
csv_data = H.google_csv_to_list(csv_url, local_csv_path)

seq = []

temps=[]


counter=0
seq_start=False

# Inspect result
for r in csv_data:
    if r[0]=="IP":
        for ip in range(1,6):
            if r[ip]!="":
                IPS.append(r[ip])
        # Turn off to cleanup
        for ip in IPS:
            off(ip)
      
        # Set starting room temp
        temps.append([room_temp for i in IPS])

    if r[0]=="alpha":
        for iii in range(1,6):
            if r[iii]!="":
                HYPER.append({'alpha':float(r[iii])})

    if r[0]=="t_max":
        for iii in range(1,6):
            if r[iii]!="":
                HYPER[iii-1]['t_max']=float(r[iii])
    
    if r[0]=="Secuencia":
        #empieza la parte secuencia
        seq_start=True
    if seq_start:
        #Convertimos las secuencias de 5 min en bloques de 1 segundo
        for b in range(step*60):
            row=[]
            for res in range(6):
                valor=False
                if r[res]!="":
                    valor=True
                row.append(valor)
            seq.append(row)

#print (seq)
#print(HYPER)

period_s = 1.0
next_tick = perf_counter() + period_s
for i, s in enumerate(seq):
    

    temprow=[]
    for index,state in enumerate(s):
        
        if index < len(IPS):
            # Calcular temperatura+
            temp=0
            t_max=HYPER[index]['t_max']
            alpha=HYPER[index]['alpha']
            
            if state:
                
                temp=T.update_temperature(temps[-1][index],True,room_temp,t_max,alpha)
                if temp>=max_temp:
                    # IF we reach the max temperature we need to cool off
                    print("*"*10,f"COOLING OFF resistencia{index}","*"*10)
                    state=False
                    temp=T.update_temperature(temps[-1][index],False,room_temp,t_max,alpha)
                    off(IPS[index])
                    
                else:
                    on(IPS[index])
            else:
                temp=T.update_temperature(temps[-1][index],False,room_temp,t_max,alpha)
                off(IPS[index])
        temprow.append(temp)    
    temps.append(temprow)

    if i % 60 == 0:
        print("minute", i // 60, strftime("%Y-%m-%d %H:%M:%S", localtime(time())), s, temprow)


    now = perf_counter()
    remaining = next_tick - now
    if remaining > 0:
        sleep(remaining)
        next_tick += period_s
    else:
        next_tick = now + period_s
        
