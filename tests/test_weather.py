import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch
try:
    from agent.tools_weather import check_weather
except (ModuleNotFoundError, AttributeError):
    from tools_weather import check_weather

def test_check_weather_past_date():
    """Prueba que retorne error si la fecha está en el pasado."""
    result = check_weather("2000-01-01")
    assert "ya pasó" in result or "No puedo consultar pronósticos en el pasado" in result

def test_check_weather_too_far_future():
    """Prueba que retorne error si la fecha es más de 16 días en el futuro."""
    result = check_weather("2099-01-01")
    assert "Open-Meteo sólo provee hasta 16 días" in result

@patch('tools_weather.requests.get')
def test_check_weather_ideal_conditions(mock_get):
    """Prueba que el reporte sea IDEAL con condiciones óptimas."""
    import datetime
    
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Mockear las respuestas de Open-Meteo
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
        def raise_for_status(self):
            pass
        def json(self):
            return self.json_data
            
    mock_daily = MockResponse({
        "daily": {
            "time": [date_str],
            "wind_speed_10m_max": [10.0],
            "wind_gusts_10m_max": [15.0],
            "precipitation_sum": [0.0],
            "temperature_2m_max": [25.0]
        }
    })
    
    mock_hourly = MockResponse({
        "hourly": {
            "cloud_cover": [0]*24 # 0% de nubes todo el día
        }
    })
    
    mock_get.side_effect = [mock_daily, mock_hourly]
    
    result = check_weather(date_str)
    
    assert "IDEAL" in result
    assert "óptimas" in result

@patch('tools_weather.requests.get')
def test_check_weather_prohibited_wind(mock_get):
    """Prueba que el reporte sea PROHIBIDO si el viento es mayor a 28."""
    import datetime
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
        def raise_for_status(self):
            pass
        def json(self):
            return self.json_data
            
    mock_daily = MockResponse({
        "daily": {
            "time": [date_str],
            "wind_speed_10m_max": [30.0], # PROHIBIDO > 28
            "wind_gusts_10m_max": [15.0],
            "precipitation_sum": [0.0],
            "temperature_2m_max": [25.0]
        }
    })
    
    mock_hourly = MockResponse({
        "hourly": {
            "cloud_cover": [0]*24
        }
    })
    
    mock_get.side_effect = [mock_daily, mock_hourly]
    
    result = check_weather(date_str)
    assert "NO SEGURO / PROHIBIDO" in result
    assert "Velocidad de viento muy alta" in result
