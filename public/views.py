import os
import json
import fitbit
import datetime
import numpy as np
import pandas as pd
import plotly.express as px
from tabulate import tabulate
import plotly.graph_objects as go
from sqlalchemy import create_engine
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from pymongo.server_api import ServerApi
from django_plotly_dash import DjangoDash
from pymongo.mongo_client import MongoClient
from django.shortcuts import render, redirect
from dash.dependencies import Input, Output, State
from django.contrib.auth.decorators import login_required



def index(request):
    context = {}

    engine = create_engine(os.environ['POSTGRES_URI'])
    sleep = pd.read_sql(f"""SELECT * FROM fitbit_sleep where date >= '2024-12-25' """, engine)
    m_sleep = sleep[['date','start_time','end_time']]
    m_sleep['date'] = m_sleep['date'].dt.date
    m_sleep['start_time'] = datetime.datetime(2025,1,1,0,0)
    m_sleep['end_time'] = m_sleep['end_time'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    m_sleep['type'] = 'sleep'

    em_sleep = sleep[['date','start_time','end_time']]
    em_sleep['date'] = em_sleep['start_time'].dt.date
    em_sleep['start_time'] = em_sleep['start_time'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    em_sleep['end_time'] = datetime.datetime(2025,1,2,0,0)
    em_sleep['type'] = 'sleep'

    pw_24_12 = pd.read_excel("Webdesk-Journal-Export--dec.xlsx")
    pw_25_01 = pd.read_excel("Webdesk-Journal-Export--jan.xlsx")
    pw_work = pd.concat([pw_24_12, pw_25_01])

    pw_work['from'] = pd.to_datetime(pw_work['from'], format='%H:%M')
    pw_work['to'] = pd.to_datetime(pw_work['to'], format='%H:%M')
    pw_work['start_time'] = pw_work['from'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    pw_work['end_time'] = pw_work['to'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    pw_work['type'] = 'work'
    pw_work['date'] = pd.to_datetime(pw_work['Date'], format='%b %d, %Y')
    pw_work = pw_work[pw_work['date']>datetime.datetime(2024,12,23)]
    pw_work.dropna(subset='start_time', how='any', inplace=True)
    print(pw_work.info())
    pw_work = pw_work[['date','start_time','end_time','type']]
    print(pw_work)


    abel_sleep = pd.concat([m_sleep, em_sleep, pw_work])
    abel_sleep['date'] = pd.to_datetime(abel_sleep['date'])
    abel_sleep.sort_values('date', inplace=True, ascending=False)
    print(abel_sleep)

    color_discrete_sequence = ['#212529']*len(abel_sleep.index)
    abel_sleep['color'] = [str(i) for i in abel_sleep.index]
    fig = px.timeline(
        abel_sleep, x_start='start_time', x_end='end_time',
        y='date', height=1000, color='type',
        color_discrete_sequence=color_discrete_sequence,
    )
    # rgb(33,37,41)
    context['fig'] = fig.to_html()

    return render(request, 'index.html', context=context)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home(request):

    context = {}

    df = pd.read_excel('personalwolke_2025.xlsx')
    df['date'] = pd.to_datetime(df['Date'])
    df['day'] = df['date'].dt.day_name()
    df['total_time'] = 24
    df[['tt_h', 'tt_m']] = df['Daily target time'].str.split(':', n=1, expand=True)
    df['work_target'] = pd.to_numeric(df['tt_h']) + pd.to_numeric(df['tt_m'])/60
    df['sleep_target'] = 8
    df['commuting_target'] = df['work_target'].apply(lambda x: 2 if x>0 else 0)

    s_row = {}
    s_row['yearly_total_time'] = df['total_time'].sum()
    s_row['yearly_work_target'] = df['work_target'].sum()
    s_row['yearly_sleep_target'] = df['sleep_target'].sum()
    s_row['yearly_commuting_target'] = df['commuting_target'].sum()
    s_row['yearly_free_time'] = df['total_time'].sum() - ( df['work_target'].sum() + df['sleep_target'].sum() + df['commuting_target'].sum() )

    summary_df = pd.DataFrame([s_row])
    summary_df = summary_df.transpose()
    summary_df = summary_df.rename(columns={0:'yearly_hours'})
    summary_df['percent'] = summary_df['yearly_hours']/summary_df.iloc[0,0]
    summary_df['days_24h'] = summary_df['yearly_hours']/24
    summary_df['weeks'] = summary_df['yearly_hours']/24/7
    summary_df['hours_per_week'] = summary_df['percent'] * 24*7

    colors = ['#dfdfdf', '#9f9f9f ', '#606060', '#202020']
    fig = go.Figure(data=[go.Pie(labels=['work','commute','sleep','free'],
                                 values=[s_row['yearly_work_target'],
                                 s_row['yearly_commuting_target'],
                                 s_row['yearly_sleep_target'],
                                 s_row['yearly_free_time']])]
    )
    fig.update_traces(hoverinfo='label+percent', textinfo='label+value+percent', textfont_size=20, marker=dict(colors=colors, line=dict(color='#000000', width=2)),)
    fig.update_layout(margin=dict(l=30,r=30,b=30,t=30))
    fig.update_layout(showlegend=False)

    df = df[['date','day','total_time','work_target','sleep_target','commuting_target']]
    context['df'] = tabulate(df.round(2), df.columns, tablefmt="psql")
    context['summary_df'] = tabulate(summary_df.round(2), summary_df.columns, tablefmt="psql")
    context['summary_fig'] = fig.to_html()


    in_app = DjangoDash(name="input_app",external_stylesheets=[dbc.themes.BOOTSTRAP])
    in_app.layout = html.Div([
        html.H6("self reported stress score (1=no stress, 5=anxious for no reason, 10=feel like breaking down)"),
        html.Div([
            dcc.Input(id='my-input', value='0', type='number'),
            html.Button('Submit', id='submit-val', n_clicks=0),
        ]),
        html.Br(),
        html.Pre(id='my-output'),

    ])

    @in_app.callback(
        Output(component_id='my-output', component_property='children'),
        Input(component_id='submit-val', component_property='n_clicks'), State(component_id='my-input', component_property='value'), prevent_initial_call=False
    )
    def update_output_div(n_clicks, input_value):
        engine = create_engine(os.environ.get('POSTGRES_SUPABASE'),)

        if n_clicks:
            ip_address_of_client = get_client_ip(request)
            df = pd.DataFrame([
                {
                'timestamp':datetime.datetime.now(),
                'ip_address': ip_address_of_client,
                'stress_score': input_value,
                }
            ])
            print(df)
            df.to_sql(f"self_reported_stress_score", con=engine, index=False, if_exists='append')

        df = pd.read_sql(f"SELECT * FROM self_reported_stress_score ORDER BY timestamp DESC LIMIT 5", con=engine)
        return tabulate(df.round(2), df.columns, tablefmt="psql")


    return render(request, 'work.html', context=context)


# 52 weeks of data collection
def week_52(request):
    context = {}
    dates = pd.DataFrame(pd.date_range(start='2025', end='2026',freq='W-MON'))
    topics = pd.DataFrame([
        'sleep from fitbit', 'expenses from ELBA', 'self reported stress level', 'analytics',
        'weather from api', 'running from app', 'distance traveled google timeline','analysis',
        'work from pw.','lines of code github','commute time','steps from fitbit','analytics',
        'siblings','2','3','analytics',
        '1','2','3','analytics',
        '1','2','3','4','analytics',
        '1','2','3','analytics',
    ])

    df = pd.merge(dates, topics, left_index=True, right_index=True, how='outer')
    def rowStyle(row):
        if row['0_x'].month % 2 == 1:
            return ['background-color: lightgrey'] * len(row)
        return [''] * len(row)

    s = df.style.apply(rowStyle, axis=1)
    context['df'] = s.to_html()
    return render(request, 'data_52.html', context=context)



def tech (request):
    context = {}
    expand_tech = []
    for file in os.listdir('static'):
        print(file)
        if file not in ['.DS_Store','.gitkeep']:
            expand_tech.append(file)
    context['technologies'] = expand_tech
    return render(request, 'tech.html', context=context)



@login_required
def sleep(request): # api request limit is 150 / hour
    context = {}

    engine = create_engine(os.environ.get('POSTGRES_RAILWAY'),)

    df = pd.read_sql(f"SELECT * FROM fitbit_sleep", engine)
    df = df.round(2)
    df = df[df['start_time'].dt.hour>18] # removes naps

    fig = px.scatter(df, x=df['date'], y=[
        df['start_time'].dt.hour.astype(float) + df['start_time'].dt.minute.astype(float)/60,
        df['end_time'].dt.hour.astype(float) + df['end_time'].dt.minute.astype(float)/60
    ], color_discrete_sequence=['#000000']*len(df))
    fig.update_layout(xaxis=dict(rangeselector=dict(),rangeslider=dict(visible=True),type="date"))
    context['fig'] = fig.to_html()
    context['df'] = tabulate(df, df.columns, tablefmt="psql")
    return render(request, "sleep.html", context=context)








#
