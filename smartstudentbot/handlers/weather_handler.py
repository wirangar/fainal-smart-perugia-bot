from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils.i18n import get_text
from utils.http import get_client
from handlers.cmd_start import UserState
from config import OPENWEATHERMAP_API_KEY, CITY_NAME as DEFAULT_CITY, DISABLE_EXTERNAL_CALLS

router = Router()

API_URL = "https://api.openweathermap.org/data/2.5/weather"

@router.message(Command("weather"))
async def cmd_weather(message: types.Message, state: FSMContext):
    """
    Handler for the /weather command.
    Fetches and displays the current weather for a specified city, or Perugia by default.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    # Extract city from command arguments, or use the default city from config
    args = message.text.split(maxsplit=1)
    city = args[1] if len(args) > 1 else DEFAULT_CITY

    if DISABLE_EXTERNAL_CALLS or not OPENWEATHERMAP_API_KEY:
        await message.answer(f"Weather feature is disabled (no API key or external calls disabled).")
        return

    params = {
        "q": city,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric", # For Celsius
        "lang": lang,
    }

    try:
        async with get_client() as client:
            response = await client.get(API_URL, params=params)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()

        # Format the success message
        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        response_message = "\n".join([
            get_text("weather_in", lang).format(city_name=data['name']),
            "---",
            get_text("weather_description", lang).format(description=weather_desc.capitalize()),
            get_text("weather_temp", lang).format(temp=f"{temp:.1f}"),
            get_text("weather_feels_like", lang).format(feels_like=f"{feels_like:.1f}"),
            get_text("weather_humidity", lang).format(humidity=humidity),
            get_text("weather_wind", lang).format(wind_speed=wind_speed),
        ])

        await message.answer(response_message)

    except Exception as e:
        # Handle different types of errors
        if hasattr(e, 'response') and e.response.status_code == 404:
            error_text = get_text("weather_city_not_found", lang).format(city_name=city)
        else:
            error_text = get_text("weather_error", lang).format(city_name=city)
            print(f"Weather API error: {e}") # Log the actual error for debugging

        await message.answer(error_text)
