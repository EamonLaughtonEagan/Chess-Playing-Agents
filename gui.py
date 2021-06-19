import PySimpleGUI as sg

sg.theme('DarkAmber') #set the coloring theme

#stuff inside the window, series of rows
layout = [ 
    [sg.Text('Row 1 text'), sg.Input(key='-IN1-')], 
    [sg.Text('Input for row 2'), sg.Input(key='-IN2-')],
    [sg.Text('Combined Output'), sg.Text('Temporary Text', key=('-OUT-'))], 
    [sg.Button('Ok'), sg.Button('Cancel'), sg.Button('Exit')] 
        ]

#create the window
window = sg.Window('This is the title of the window', layout)

#create event loop for processing events and geting values of inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Exit': #if window is closed or clicks cancel
        break
    window['-OUT-'].update(values['-IN1-'] + ' ' + values['-IN2-'])

window.close()