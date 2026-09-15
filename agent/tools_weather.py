import datetime
import requests

LATITUDE = 14.013722
LONGITUDE = -90.771611

def check_weather(date_str: str) -> str:
    """
    Verifica las condiciones climáticas para un día en específico para saber si es apto para salto en paracaídas.
    El parámetro date_str debe ser un string en formato YYYY-MM-DD.
    El pronóstico está limitado a un máximo de 16 días en el futuro.
    
    Retorna un string con el reporte del clima y si el día es IDEAL, MARGINAL o NO SEGURO/PROHIBIDO.
    """
    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Error: La fecha proporcionada debe estar en formato YYYY-MM-DD."
    
    today = datetime.date.today()
    delta_days = (target_date - today).days
    
    if delta_days < 0:
        return f"Error: La fecha {date_str} ya pasó. No puedo consultar pronósticos en el pasado."
    
    if delta_days > 15:
        return f"Error: No puedo pronosticar para la fecha {date_str}. Open-Meteo sólo provee hasta 16 días de predicción."
    
    # URL para consultar el forecast diario
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max&"
        f"timezone=auto&start_date={date_str}&end_date={date_str}"
    )
    
    # URL para hourly y sacar promedio de cobertura de nubes
    url_cloud = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"hourly=cloud_cover&"
        f"timezone=auto&start_date={date_str}&end_date={date_str}"
    )

    try:
        response_daily = requests.get(url, timeout=10)
        response_daily.raise_for_status()
        data_daily = response_daily.json()
        
        response_hourly = requests.get(url_cloud, timeout=10)
        response_hourly.raise_for_status()
        data_hourly = response_hourly.json()
    except requests.RequestException as e:
        return f"Error al consultar la API de Open-Meteo: {e}"

    if "daily" not in data_daily or not data_daily["daily"].get("time"):
        return "Error: No se obtuvieron datos diarios para la fecha solicitada."

    wind_speed = data_daily["daily"]["wind_speed_10m_max"][0]
    wind_gusts = data_daily["daily"]["wind_gusts_10m_max"][0]
    precipitation = data_daily["daily"]["precipitation_sum"][0]
    temperature = data_daily["daily"]["temperature_2m_max"][0]

    # Promedio de nubes asumiendo horas diurnas (8:00 a 17:00)
    cloud_covers = data_hourly["hourly"]["cloud_cover"][8:18]
    avg_cloud_cover = sum(cloud_covers) / len(cloud_covers) if cloud_covers else 0

    # Lógica de validación
    status = "IDEAL"
    reasons = []

    if precipitation > 0.0:
        status = "NO SEGURO / PROHIBIDO"
        reasons.append("Precipitación detectada. Saltar con lluvia daña el equipo y lastima la piel.")

    if wind_gusts > 35.0:
        status = "NO SEGURO / PROHIBIDO"
        reasons.append(f"Ráfagas altas ({wind_gusts} km/h).")

    if wind_speed > 28.0:
        status = "NO SEGURO / PROHIBIDO"
        reasons.append(f"Velocidad de viento muy alta ({wind_speed} km/h).")
    elif 20.0 <= wind_speed <= 28.0:
        if status != "NO SEGURO / PROHIBIDO":
            status = "MARGINAL"
        reasons.append(f"Viento marginal ({wind_speed} km/h). Solo tándem experimentado.")

    if avg_cloud_cover > 75.0:
        status = "NO SEGURO / PROHIBIDO"
        reasons.append(f"Nubes muy altas ({avg_cloud_cover:.1f}%). Impide reglas VFR.")
    elif 30.0 <= avg_cloud_cover <= 75.0:
        if status != "NO SEGURO / PROHIBIDO":
            status = "MARGINAL"
        reasons.append(f"Nubes dispersas ({avg_cloud_cover:.1f}%).")
    
    if not reasons:
        reasons.append("Condiciones óptimas.")

    reporte = (
        f"Pronóstico {date_str}:\n"
        f"Temp max: {temperature}°C\n"
        f"Viento: {wind_speed} km/h (Rafagas: {wind_gusts} km/h)\n"
        f"Precipitación: {precipitation} mm\n"
        f"Nubes: {avg_cloud_cover:.1f}%\n"
        f"STATUS: {status}\n"
        f"Detalles: {', '.join(reasons)}"
    )
    return reporte

WEATHER_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "check_weather",
        "description": "Verifica si el clima es apto para saltar en paracaídas para una fecha dada.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "La fecha a consultar en formato YYYY-MM-DD (Ej. 2026-10-05)"
                }
            },
            "required": ["date_str"]
        }
    }
}
