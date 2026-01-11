

import csv
import requests
from io import StringIO

csv_url='https://docs.google.com/spreadsheets/d/e/2PACX-1vTV-Hit42Sq3zXsn88tFLRb7S4cpt-TCHuHI1tdbLnsVxe1CuwT9j650IehaBuhsu40vFnNvL18eqJb/pub?output=csv'
step=5 #minutos

def google_csv_to_list(url):
    # Download the CSV content
    response = requests.get(url)
    response.raise_for_status()  

    # Convert text into a file-like object
    csv_file = StringIO(response.text)

    # Read CSV into list of lists
    reader = csv.reader(csv_file)
    data = [row for row in reader]

    return data



csv_data = google_csv_to_list(csv_url)

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

print (seq)