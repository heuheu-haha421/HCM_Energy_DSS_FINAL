import meteostat as ms
import pandas as pd
from app.errors import NotFoundError

class Weather:
    def __init__(self, location, start, end):
        self.location = location
        self.start    = start
        self.end      = end

    def get_weather_data(self):
        ts       = ms.daily(self.location, self.start, self.end)
        df_daily = ts.fetch()
        
        if df_daily is None or df_daily.empty:
            raise NotFoundError("No weather data found for the specified location and date range.")

        weekly_weather = df_daily.resample('W-MON', closed='left', label='left').agg({
            'temp': 'mean', # Temperature
            'tmin': 'min',  # Temperature Min
            'tmax': 'max',  # Temperature Max
            'rhum': 'mean', # Relative Humidity
            'prcp': 'sum',  # Precipitation
            'wspd': 'mean', # Wind Speed
            'pres': 'mean', # Pressure

        }).round(1)

        return weekly_weather.iloc[[-1]]
    
if __name__ == "__main__":
    location   = "48900"                       # Tan Son Nhat Station ID
    start_date = pd.to_datetime("2026-04-20")
    end_date   = pd.to_datetime("2026-04-26")

    weather      = Weather(location, start_date, end_date)
    weather_data = weather.get_weather_data()
    