import requests
import pandas as pd
import json
from io import StringIO
from typing import Optional

class RenewablesNinjaAPI:
    """Handler for Renewables.ninja API"""
    def __init__(self, api_token: str):
        self.token = api_token
        self.api_base = 'https://www.renewables.ninja/api/'
        self.session = requests.Session()
        self.session.headers = {'Authorization': f'Token {self.token}'}

    def fetch_pv_data(
        self,
        lat: float,
        lon: float,
        date_from: str,
        date_to: str,
        capacity: float,
        system_loss: float = 0.1,
        tracking: int = 0,
        tilt: float = 25,
        azim: float = 180
    ) -> pd.Series:
        """Fetch solar PV generation data"""
        url = f'{self.api_base}data/pv'
        params = {
            'lat': lat,
            'lon': lon,
            'date_from': date_from,
            'date_to': date_to,
            'dataset': 'merra2',
            'capacity': capacity,
            'system_loss': system_loss,
            'tracking': tracking,
            'tilt': tilt,
            'azim': azim,
            'format': 'json',
            'local_time': 'true'
        }
        
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # Convert to DataFrame
            df = pd.read_json(StringIO(json.dumps(data['data'])), orient='index')
            df.index = pd.to_datetime(df.index)
            return df['electricity']  # Return the electricity generation column
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}") 