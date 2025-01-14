import os
import json
import scipy
import fitbit
import datetime
import sqlalchemy
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.express as px
from tabulate import tabulate
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from pymongo.server_api import ServerApi
from django_plotly_dash import DjangoDash
from pymongo.mongo_client import MongoClient
from django.shortcuts import render, redirect
from dash.dependencies import Input, Output, State
from django.contrib.auth.decorators import login_required

# 🌟 star, 🚀


def index(request):
    context = {}
    engine = create_engine(os.environ['POSTGRES_URI'], client_encoding='utf8')
    sleep = pd.read_sql(
        f"""SELECT * FROM fitbit_sleeping where "dateOfSleep" >= '2024-12-25' AND "isMainSleep" = True """,
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
    pw_25_01 = pd.read_excel("Webdesk-Journal-Export--jan.xlsx")
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
        xaxis_range=[datetime.datetime(2025,1,1,0,0,0), datetime.datetime(2025,1,2,0,0,0)],
        bargap=0.05,
        xaxis_tickformat="%H",
        plot_bgcolor='rgb(246,244,242)',
        title_font_family="Arial",
        title_font_color="black",
        margin=dict(l=0,r=0,b=60,t=30)
    )
    fig.layout.font.family = 'Arial'
    fig.layout.font.size = 16
    fig.update_yaxes(visible=False, nticks=int(len(abel_sleep.index)/2))
    fig.update_xaxes(nticks=24)
    context['fig'] = fig.to_html()

    return render(request, 'index.html', context=context)


def abel(request):
    context = {}
    expand_tech = []
    for file in os.listdir('static'):
        if file not in ['.DS_Store','.gitkeep']:
            expand_tech.append(file)
    context['technologies'] = expand_tech

    engine = create_engine(os.environ['POSTGRES_URI'], client_encoding='utf8')
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
    print(df.info())

    context['df'] = df[[
        'dateOfSleep','duration_hours'
    ]].round(2).to_html()


    app = DjangoDash(name="correlations",external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div([
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(['NYC', 'MTL', 'SF'], 'NYC', id='x-input'),
                dcc.Dropdown(['NYC', 'MTL', 'SF'], 'NYC', id='y-input'),
            ], width=4),
            dbc.Col([
                dcc.Graph(id="scatter-plot"),
            ], width=8),
        ])
    ])

    @app.callback(
        Output("scatter-plot", "figure"),
        Input("x-input", "value"),Input("y-input", "value"))
    def update_bar_chart(x, y):
        ddf = df[df['isMainSleep']==True]
        fig = px.scatter(ddf, x="efficiency", y="duration_hours", trendline='ols')
        return fig



    #correclation = scipy.stats.linregress( ddf['efficiency'],ddf['duration_hours'],)
    #print(correclation)


    return render(request, 'private/abel.html', context=context)

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
        engine = create_engine(os.environ['POSTGRES_URI'], client_encoding='utf8')

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



#
