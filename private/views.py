import os
import io
import base64
import fitbit
import inspect
import datetime
import pandas as pd
import plotly.express as px
from django.shortcuts import render, redirect
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash
from dash.dependencies import Input, Output, State
from .helper_gh import abel_gh_auth, abel_put_file, abel_get_file, gather_oauth




def index(reuqest):
    
    return 0


def ingestion(request):
    context = {}
    
    app = DjangoDash("ingestion", update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div([
        dcc.Graph(id='sleep'),
    ])
    
    return render(request, 'ingestion.html', context=context)


'''

def expenses(request):
    
    
    app = DjangoDash("expenses", update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div([
        dcc.Upload( id='upload-data', children=html.Div(['Drag and Drop or ', html.A('Select Files') ]),
            style={
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=True
        ),
        html.Div(id='output-data-upload'),
    ])

    def parse_contents(contents, filename, date):
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                if "Umsatzliste" in filename:   # uploading expenses
                    df = pd.read_csv( io.StringIO(decoded.decode('utf-8')), delimiter=';')
                    
            elif 'xls' in filename:
                df = pd.read_excel(io.BytesIO(decoded))
        except Exception as e:
            print(e)
            return html.Div([
                'There was an error processing this file.'
            ])

        return html.Div([
            html.H5(filename),
            html.H6(datetime.datetime.fromtimestamp(date)),

            dash_table.DataTable(
                df.to_dict('records'),
                [{'name': i, 'id': i} for i in df.columns]
            ),
            html.Hr(),  # horizontal line
            # For debugging, display the raw contents provided by the web browser
            html.Div('Raw Content'),
            html.Pre(contents[0:200] + '...', style={
                'whiteSpace': 'pre-wrap',
                'wordBreak': 'break-all'
            })
        ])

    @app.callback(Output('output-data-upload', 'children'),
                Input('upload-data', 'contents'),
                State('upload-data', 'filename'),
                State('upload-data', 'last_modified'))
    def update_output(list_of_contents, list_of_names, list_of_dates):
        if list_of_contents is not None:
            children = [
                parse_contents(c, n, d) for c, n, d in
                zip(list_of_contents, list_of_names, list_of_dates)]
            return children
        
    return 0
    
'''