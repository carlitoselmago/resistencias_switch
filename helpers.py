import requests
import csv
from io import StringIO

class helpers():
    

    def __init__(self):
        pass

    def read_csv_text(self,text):
        csv_file = StringIO(text)
        reader = csv.reader(csv_file)
        return [row for row in reader]


    def google_csv_to_list(self,url, local_path):
        try:
            # Try downloading from internet
            print("Downloading CSV from Google Sheets...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Save locally
            local_path.write_text(response.text, encoding="utf-8")

            return self.read_csv_text(response.text)

        except Exception as e:
            print(f"Download failed ({e})")

            # Fallback to local file
            if local_path.exists():
                print("Using cached local CSV")
                text = local_path.read_text(encoding="utf-8")
                return self.read_csv_text(text)
            else:
                raise RuntimeError("No internet connection and no local CSV cache found")