import os
import json
import scipy
import fitbit
import datetime
import sqlalchemy
import numpy as np
import pandas as pd
import connectorx as cx
import plotly.express as px
from tabulate import tabulate
import plotly.graph_objects as go
from django.http import HttpResponse
from sqlalchemy import create_engine, text
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash
from django.shortcuts import render, redirect
from dash.dependencies import Input, Output, State
from django.contrib.auth.decorators import login_required

from functools import wraps
from time import time

def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print(f"\n\nfunc:%r args:[%r, %r] took: %2.4f sec" % \
          (f.__name__, args, kw, te-ts))
        return result
    return wrap

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
# 🌟 star, 🚀

@login_required
def index(request):
    context = {}
    engine = create_engine(os.environ['POSTGRES_URI'], client_encoding='utf8')
    sleep = pd.read_sql(
        f"""SELECT * FROM fitbit_sleeping where
        "dateOfSleep" >= '2024-12-25' AND "isMainSleep" = True """,
        con=engine,
        dtype={'dateOfSleep':'datetime64[ns]', 'startTime':'datetime64[ns]', 'endTime':'datetime64[ns]'},
    )
    m_sleep = sleep[['dateOfSleep','startTime','endTime']]
    m_sleep['date'] = m_sleep['dateOfSleep'].dt.date
    m_sleep['start_time'] = datetime.datetime(2025,1,1,0,0)
    m_sleep['end_time'] = m_sleep['endTime'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    m_sleep['type'] = 'sleep'

    em_sleep = sleep[['dateOfSleep','startTime','endTime']]
    em_sleep['date'] = em_sleep['dateOfSleep'].dt.date - datetime.timedelta(days=1)
    em_sleep['start_time'] = em_sleep['startTime'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    em_sleep['end_time'] = datetime.datetime(2025,1,2,0,0)
    em_sleep['type'] = 'sleep'

    pw_24_12 = pd.read_excel("Webdesk-Journal-Export--dec.xlsx")
    pw_25_01 = pd.read_excel("Webdesk-Journal-Export--2025-01.xlsx")
    pw_work = pd.concat([pw_24_12, pw_25_01])
    pw_work['from'] = pd.to_datetime(pw_work['from'], format='%H:%M')
    pw_work['to'] = pd.to_datetime(pw_work['to'], format='%H:%M')
    pw_work['start_time'] = pw_work['from'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    pw_work['end_time'] = pw_work['to'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    pw_work['type'] = 'work'
    pw_work['date'] = pd.to_datetime(pw_work['Date'], format='%b %d, %Y')
    pw_work.dropna(subset='start_time', how='any', inplace=True)
    pw_work = pw_work[['date','start_time','end_time','type']]


    runs = pd.read_sql(f""" SELECT * FROM running where "time" >= '2024-12-26' """, con=engine)
    runs_start = pd.DataFrame(runs.groupby('run_id')['time'].min())
    runs_end = pd.DataFrame(runs.groupby('run_id')['time'].max())
    runs = pd.merge(
        runs_start, runs_end,
        left_on='run_id', right_on='run_id',
        suffixes=['_start','_end']
    )
    runs['date'] = runs['time_start'].dt.date
    runs['start_time'] = runs['time_start'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    runs['end_time'] = runs['time_end'].apply(lambda dt: dt.replace(year=2025, month=1, day=1))
    runs['type'] = 'run'
    runs = runs[['date','start_time','end_time','type']]


    abel_sleep = pd.concat([m_sleep, em_sleep, pw_work, runs ])
    abel_sleep['date'] = pd.to_datetime(abel_sleep['date'])
    abel_sleep = abel_sleep[abel_sleep['date']>datetime.datetime(2024,12,25)]
    abel_sleep.sort_values('date', inplace=True, ascending=False)
    abel_sleep['start_time'] = pd.to_datetime(abel_sleep['start_time'], utc=True)
    abel_sleep['end_time'] = pd.to_datetime(abel_sleep['end_time'], utc=True)
    abel_sleep['label'] = abel_sleep['date'].dt.strftime("%a %d %b")
    abel_sleep = abel_sleep.reset_index()
    abel_sleep.drop_duplicates(subset=['date','start_time'], inplace=True)

    def mask(row):
       if row["start_time"].hour != 0:
          row["label"] = ""
       return row

    abel_sleep = abel_sleep.apply(mask, axis=1)
    print(abel_sleep)
    fig = px.timeline(
        abel_sleep, x_start='start_time', x_end='end_time',
        y='date', text='label',
        hover_data=["type"],
        height=len(abel_sleep.index)*20,
    )
    colormap = {s:c for s,c in zip(abel_sleep["type"].unique(), px.colors.qualitative.Pastel2)}
    fig.update_traces(
        marker_color=[colormap[s[0]] for s in fig.data[0].customdata],
        insidetextanchor="start",
        textposition="auto",
    )
    fig.update_layout(
        title_text='sleep work and run times / day', title_x=0.5,
        title_font_family="Arial",
        title_font_color="black",
        xaxis_range=[datetime.datetime(2025,1,1,0,0,0), datetime.datetime(2025,1,2,0,0,0)],
        xaxis_tickformat="%H",
        bargap=0.05,
        plot_bgcolor='rgb(246,244,242)',
        margin=dict(l=0,r=0,b=60,t=30)
    )
    fig.layout.font.family = 'Arial'
    fig.layout.font.size = 16
    fig.update_yaxes(visible=False, nticks=int(len(abel_sleep.index)/2))
    fig.update_xaxes(nticks=24)
    context['fig'] = fig.to_html()

    return render(request, 'index.html', context=context)

@timing
def get_client():
    return str(os.environ['POSTGRES_URI']).replace('postgresql://','postgres://')

@timing
def get_df(conn):
    df = cx.read_sql(conn, f"SELECT * FROM thoughts")
    df['timestamp'] = df['timestamp'].astype(str)
    return df

@timing
def myajaxformview(request):
    engine = get_client()
    df = get_df(engine)
    data = df.to_dict(orient='records')
    return HttpResponse(json.dumps({'data': data}), content_type="application/json")

@timing
@login_required
def abel(request):
    context = {}
    expand_tech = []
    for file in os.listdir('static'):
        if file not in ['.DS_Store','.gitkeep']:
            expand_tech.append(file)
    context['technologies'] = expand_tech

    engine = create_engine(os.environ['POSTGRES_URI'])
    df = pd.read_sql(
        f"""SELECT
        "awakeCount"
         "awakeDuration",
         "awakeningsCount",
         "dateOfSleep",
         "duration",
         ("timeInBed"::float / 60) as "duration_hours",
         "endTime"::timestamp - "startTime"::timestamp as "duration_timestamp",
         "efficiency",
         "endTime",
         "isMainSleep",
         "logId",
         "minuteData",
         "minutesAfterWakeup",
         "minutesAsleep",
         "minutesAwake",
         "minutesToFallAsleep",
         "restlessCount",
         "restlessDuration",
         "startTime",
         "timeInBed"
        FROM fitbit_sleeping where "dateOfSleep" >= '2024-12-26' """,
        con=engine,
        dtype={'dateOfSleep':'datetime64[ns]', 'startTime':'datetime64[ns]', 'endTime':'datetime64[ns]'},
    )
    df.drop_duplicates('startTime',inplace=True)

    context['df'] = df[[
        'dateOfSleep','duration_hours','startTime',
    ]].round(2).to_html()

    # correlations application
    app = DjangoDash(name="correlations",external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = dbc.Row([
        dbc.Col([
            dcc.Dropdown(df.select_dtypes(include='number').columns, 'duration_hours', id='x'),
            dcc.Dropdown(df.select_dtypes(include='number').columns, 'efficiency', id='y'),], className='my-auto'),
        dbc.Col([], id='abel'),
    ], className=['m-5 text-center'])

    @app.callback(Output("abel", "children"), Input("x", "value"), Input("y", "value"))
    def update_bar_chart(x, y):
        ddf = df[df['isMainSleep']==True].copy(deep=True)
        r = scipy.stats.linregress(ddf[x],ddf[y])
        TO_ROUND = 4
        return html.Div([
            dcc.Graph(figure=px.scatter(ddf, x=x, y=y, trendline='ols')),
            html.P(f"pvalue: {r.pvalue}"),
            html.P(f"slope: {round(r.slope,TO_ROUND)}"),
            html.P(f"intercept: {round(r.intercept,TO_ROUND)}"),
            html.P(f"rvalue: {round(r.rvalue,TO_ROUND)}"),
            html.P(f"stderr: {round(r.stderr,TO_ROUND)}"),
            html.P(f"intercept_stderr: {round(r.intercept_stderr,TO_ROUND)}\n"),
        ])

    ddf = pd.DataFrame(
        df.groupby('dateOfSleep').agg({'dateOfSleep':'size','duration_hours':['sum','mean','std']})
    )

    context['label_series'] = json.dumps(list(ddf.index.strftime('%-j').astype(str)))
    context['value_series'] = json.dumps(ddf['duration_hours']['sum'].to_list())

    return render(request,'abel.html',context=context)


# tabulate(df.round(2), df.columns, tablefmt="psql")

@login_required
def dot(request):
    import graphviz
    for engine in ['circo', 'dot', 'fdp', 'neato', 'osage', 'patchwork', 'sfdp', 'twopi']:
        dot = graphviz.Digraph("hello-pythonistas", comment="Hello world example", engine=engine,)
        dot.edge("test", "a")
        dot.edge("test", "b")
        dot.edge("b", "a")
        dot.edge("b", "abel")
        dot.render(filename=f"{engine}", format='png', directory='static/dot')
    expand_tech = []
    for file in os.listdir('static/dot'):
        if '.png' in file:
            expand_tech.append(f"dot/{file}")

    return render(request, 'dot.html', context={'technologies':expand_tech})



# PUBLIC fetches last 13 days of sleep
def fetch_fitbit(request):
    import cherrypy
    import sys
    import threading
    import traceback
    import webbrowser
    from urllib.parse import urlparse
    from base64 import b64encode
    from fitbit.api import Fitbit
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError, MissingTokenError


    class OAuth2Server:
        def __init__(self, client_id, client_secret, redirect_uri='http://127.0.0.1:8080/'):
            self.success_html = """<p>You authorized the Fitbit API!</p>"""
            self.failure_html = """<h1>ERROR: %s</h1><br/><h3>You can close this window</h3>%s"""
            self.fitbit = Fitbit( client_id, client_secret, redirect_uri=redirect_uri, timeout=10,)
            self.redirect_uri = redirect_uri

        def browser_authorize(self):
            url, _ = self.fitbit.client.authorize_token_url()
            threading.Timer(1, webbrowser.open, args=(url,)).start()
            urlparams = urlparse(self.redirect_uri)
            cherrypy.config.update({'server.socket_host': urlparams.hostname, 'server.socket_port': urlparams.port})
            cherrypy.quickstart(self)

        @cherrypy.expose
        def index(self, state, code=None, error=None):
            error = None
            if code:
                try: self.fitbit.client.fetch_access_token(code)
                except MissingTokenError: error = self._fmt_failure('Missing access token parameter.</br>Please check the correct client_secret')
                except MismatchingStateError: error = self._fmt_failure('CSRF Warning! Mismatching state')
            else:
                error = self._fmt_failure('Unknown error while authenticating')
            self._shutdown_cherrypy()
            return error if error else self.success_html

        def _fmt_failure(self, message):
            tb = traceback.format_tb(sys.exc_info()[2])
            tb_html = '<pre>%s</pre>' % ('\n'.join(tb)) if tb else ''
            return self.failure_html % (message, tb_html)

        def _shutdown_cherrypy(self):
            if cherrypy.engine.state == cherrypy.engine.states.STARTED:
                threading.Timer(1, cherrypy.engine.exit).start()

    server = OAuth2Server("23PHFZ", os.environ['FITBIT_CLIENT_SECRET'])
    server.browser_authorize()

    tokens = {}
    for key, value in server.fitbit.client.session.token.items():
        tokens[key] = value
    authd_client = fitbit.Fitbit( "23PHFZ", "public", tokens['access_token'], tokens['refresh_token'] )

    days_data_avaliable = (datetime.datetime.now() - datetime.datetime(2024,5,27)).days + 1
    date_list = [datetime.datetime(2024,5,27) + datetime.timedelta(days=x) for x in range(days_data_avaliable)]
    date_list.reverse()

    fitbit_client = fitbit.Fitbit( "23PHFZ", "public", tokens['access_token'], tokens['refresh_token'] )
    engine = create_engine(os.environ['POSTGRES_URI'], client_encoding='utf8')

    for date in date_list[0:10]:
        sleep_data = fitbit_client.sleep(date)
        if len(sleep_data['sleep']):
            durration_df = pd.DataFrame(sleep_data['sleep'])
            try:
                with engine.connect() as conn:
                    conn.execute(text(f"DELETE FROM fitbit_sleep WHERE date='{date}' "))
                    conn.commit()
            except Exception as e:
                print(e)
            durration_df.to_sql(
                f"fitbit_sleeping", con=engine, index=False, if_exists='append',
                dtype={"minuteData": sqlalchemy.types.JSON},
            )
        else:
            print(f"no sleep")

    return redirect('/')
