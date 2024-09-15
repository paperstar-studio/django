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
from pymongo.server_api import ServerApi
from django_plotly_dash import DjangoDash
from pymongo.mongo_client import MongoClient
from dash.dependencies import Input, Output, State
from .helper_gh import abel_gh_auth, abel_put_file, abel_get_file, gather_oauth


def mongo_db_upload(client, db, df):
    mydb = client["public"]
    mycol = mydb[db]
    outcome = mycol.insert_many(df.to_dict('records'))
    print(outcome)
    return 0

def mongo_db_delete(client, db):
    mydb = client["public"]
    mycol = mydb[db]
    outcome = mycol.delete_many({})
    print(outcome)
    return 0

def mongo_db_read(client, db):
    mydb = client["public"]
    mycol = mydb[db]
    cursor = mycol.find({})
    df =  pd.DataFrame(list(cursor))
    return df

def style_figure(fig, showlegend=False):
    padding = 100
    fig.update_layout(showlegend=showlegend)
    fig['layout']['yaxis']['showgrid'] = False
    #fig['layout']['xaxis']['showgrid'] = False
    #fig['layout']['plot_bgcolor'] = 'rgba(242, 192, 192, 0.2)'
    fig['layout']['margin'] = dict(l=padding,r=padding,t=padding,b=padding)
    fig.update_yaxes(visible=False, showticklabels=False)
    #fig.update_xaxes(visible=False, showticklabels=False)
    color = 'rgb(242, 192, 192)'#'#83B4F7'#BFE9DD' #'#83B4F7'
    fig.update_layout({ 'paper_bgcolor': color, 'plot_bgcolor': color, 'xaxis_title': ""})
    #fig.update_layout({ 'paper_bgcolor': '#83B4F7',})
    return fig



def index(reuqest):
    context = {}
    
    uri = os.getenv("MONGO_DB_CLIENT") 
    client = MongoClient(uri, server_api=ServerApi('1'))
    df = mongo_db_read(client, 'expenses')
    print(df.info())
    df.sort_values('date', inplace=True, ascending=False)
    
    expenses_income = df.copy(deep=True)
    expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Recipient IBAN: AT933200000013349683')]
    expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Client IBAN: AT933200000013349683')]
    expenses_income = expenses_income[~expenses_income['purpose'].str.contains('AT260100000005504068')] # finanzampt
    
    app = DjangoDash("expenses", update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div([
        dcc.Graph(id='expenses'),
        dcc.Graph(id='expenses_edited'),
    ])
    
    @app.callback( Output("expenses", "figure"), Input("expenses", "figure") )
    def expenses_graph(n_clicks):
        uri = os.getenv("MONGO_DB_CLIENT") 
        client = MongoClient(uri, server_api=ServerApi('1'))
        df = mongo_db_read(client, 'expenses')
        df.sort_values('date', inplace=True, ascending=False)
        expenses_income = df.copy(deep=True)
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Recipient IBAN: AT933200000013349683')]
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Client IBAN: AT933200000013349683')]
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('AT260100000005504068')] # finanzampt
    
        expenses_income = expenses_income[expenses_income['amount']<0]
        
        fig = px.scatter(expenses_income, x='date',y='amount')
        fig.update_layout(title_text='expenses - total', title_x=0.5)
        return style_figure(fig)
    
    
    @app.callback( Output("expenses_edited", "figure"), Input("expenses_edited", "figure") )
    def expenses_trimmed_graph(n_clicks):
        uri = os.getenv("MONGO_DB_CLIENT") 
        client = MongoClient(uri, server_api=ServerApi('1'))
        df = mongo_db_read(client, 'expenses')
        df.sort_values('date', inplace=True, ascending=False)
        expenses_income = df.copy(deep=True)
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Recipient IBAN: AT933200000013349683')]
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Client IBAN: AT933200000013349683')]
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('AT260100000005504068')] # finanzampt
    
        expenses_income = expenses_income[expenses_income['amount']<0]
        print(expenses_income.info())
        
        for i in expenses_income['purpose']:
            print(i)
            print()
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Purpose of use: ATM S6EE1113 WIEN 1160 Payment reference: ATM 250,00 AT D4 06.08. 19:35 Card sequence no: 4')]
        expenses_income = expenses_income[~expenses_income['purpose'].str.contains('Purpose of use: ATM S6EE1113 WIEN 1160 Payment reference: ATM 400,00 AT D4 06.08. 19:34 Card sequence no: 4')] 
        print(expenses_income.info())
        
        fig = px.scatter(expenses_income, x='date',y='amount')
        fig.update_layout(title_text='expenses - edited', title_x=0.5)
        return style_figure(fig)
    
    context['df'] = df[['date','purpose','amount']].to_html(index=False, escape=False),
    return render(reuqest, 'private.html', context=context)






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