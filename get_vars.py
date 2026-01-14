from temp import temp
from helpers import helpers
from pathlib import Path

H=helpers()

csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?gid=1438086701&single=true&output=csv"
local_csv_path = Path("cached_google_sheet_medidas.csv")
csv_data = H.google_csv_to_list(csv_url, local_csv_path)

readings=[[],[],[],[],[],[]]



for i,r in enumerate(csv_data):
    if i>0:
        for ii,col in enumerate(r):
            if ii>0:
                if col!="":
                    readings[ii-1].append(col)
#print(readings)


for i,r in enumerate(readings):

    if len(r)>0:
        print(":"*80)
        print(f"PROCESSING RESISTENCIA index {i}")
        print(":"*80)
        print()

        temps = [float(i) for i in r]
        print(temps)

        model = temp()

        alpha, T_max = model.estimate_alpha_and_Tmax(
            temperatures=temps,
            T_ambient=21.5
        )

        print("alpha:", alpha)
        print("T_max:", T_max)

