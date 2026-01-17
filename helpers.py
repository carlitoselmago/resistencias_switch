import requests
import csv
from io import StringIO
from pathlib import Path

class helpers():
    

    def __init__(self):
        pass

    def read_csv_text(self, text):
            csv_file = StringIO(text)
            reader = csv.reader(csv_file)
            return list(reader)

    def google_csv_to_list(self, url, local_path):
        local_path = Path(local_path)

        try:
            print("→ Downloading CSV from Google Sheets...")
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            # Very common Google failure case
            if "<html" in response.text.lower():
                raise ValueError("Google returned HTML instead of CSV")

            print("→ Download OK, saving locally")
            local_path.write_text(response.text, encoding="utf-8")

            print("→ Parsing CSV")
            return self.read_csv_text(response.text)

        except Exception as e:
            print(f"⚠ Download failed: {e}")

            if local_path.exists():
                print("→ Using cached local CSV")
                text = local_path.read_text(encoding="utf-8")
                return self.read_csv_text(text)

            raise RuntimeError("No internet connection and no local CSV cache found")