import csv
import requests
from io import StringIO
from pathlib import Path
from time import sleep

csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?output=csv"
local_csv_path = Path("cached_google_sheet.csv")
step=5 #minutos de pause entre step

def read_csv_text(text):
    csv_file = StringIO(text)
    reader = csv.reader(csv_file)
    return [row for row in reader]


def google_csv_to_list(url, local_path):
    try:
        # Try downloading from internet
        print("Downloading CSV from Google Sheets...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Save locally
        local_path.write_text(response.text, encoding="utf-8")

        return read_csv_text(response.text)

    except Exception as e:
        print(f"Download failed ({e})")

        # Fallback to local file
        if local_path.exists():
            print("Using cached local CSV")
            text = local_path.read_text(encoding="utf-8")
            return read_csv_text(text)
        else:
            raise RuntimeError("No internet connection and no local CSV cache found")


# Usage
csv_data = google_csv_to_list(csv_url, local_csv_path)

seq = []

counter=0
seq_start=False

# Inspect result
for r in csv_data:
    if r[0]=="Secuencia":
        #empieza la parte secuencia
        seq_start=True
    if seq_start:
        row=[]
        for res in range(6):
            valor=False
            if r[res]!="":
                valor=True
            row.append(valor)
        seq.append(row)

#print (seq)

for i,s in enumerate(seq):
    minuto=i*step
    print(f"step {minuto} minutos")
    print(s)
    sleep(step*60)