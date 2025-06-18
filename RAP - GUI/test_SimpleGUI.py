import PySimpleGUI as sg
from datetime import datetime
import webbrowser

sg.theme("LightGrey1")

current_date = datetime.now().strftime("%Y-%m-%d")

def open_map(lat, lon):
    url = f"https://www.google.com/maps?q={lat},{lon}"
    webbrowser.open(url)

layout = [
    [sg.Text("Greeting App", background_color="blue", text_color="white", font=("Arial", 14), size=(30,1), justification='center')],
    [sg.Text("Enter your name:")],
    [sg.InputText()],
    [sg.Text("Enter latitude:"), sg.InputText(key="LAT")],
    [sg.Text("Enter longitude:"), sg.InputText(key="LON")],
    [sg.Button("Greet"), sg.Button("Show Map"), sg.Button("Exit")],
    [sg.Text("", size=(30,1), key='-OUTPUT-')],
    [sg.Text(f"Date: {current_date}", text_color="gray", justification='right')]
]

window = sg.Window("Greeting App", layout, finalize=True)

while True:
    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    if event == "Greet":
        name = values[0]
        window['-OUTPUT-'].update(f"Hello, {name}!")
    if event == "Show Map":
        try:
            lat = float(values["LAT"])
            lon = float(values["LON"])
            open_map(lat, lon)
        except ValueError:
            sg.popup("Please enter valid latitude and longitude numbers.")

window.close()