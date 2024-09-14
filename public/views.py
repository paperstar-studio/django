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




def style_figure(fig):
    padding = 60
    fig.update_layout(showlegend=False)
    fig['layout']['yaxis']['showgrid'] = False
    #fig['layout']['xaxis']['showgrid'] = False
    #fig['layout']['plot_bgcolor'] = 'rgba(242, 192, 192, 0.2)'
    fig['layout']['margin'] = dict(l=padding,r=padding,t=padding,b=padding)
    fig.update_yaxes(visible=False, showticklabels=False)
    #fig.update_xaxes(visible=False, showticklabels=False)
    color = '#BFE9DD' #'#83B4F7'
    fig.update_layout({ 'paper_bgcolor': color, 'plot_bgcolor': color, 'xaxis_title': ""})
    #fig.update_layout({ 'paper_bgcolor': '#83B4F7',})
    return fig


def index(request):
    context = {}

    app_sleep = DjangoDash("sleep", update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_sleep.layout = html.Div([
        dcc.Graph(id='sleep'),
    ])
    
    @app_sleep.callback( Output("sleep", "figure"), Input("sleep", "figure") )
    def sleep_graph(n_clicks):
        g, u = abel_gh_auth()
        df = pd.read_csv(abel_get_file(g, u, 'fitbit_sleep.csv'), parse_dates=['start_time', 'end_time']).sort_values('date')
        fig = px.scatter(df, x=df['date'], y=[
            df['start_time'].dt.hour.astype(float) + df['start_time'].dt.minute.astype(float)/60,
            df['end_time'].dt.hour.astype(float) + df['end_time'].dt.minute.astype(float)/60
        ], color_discrete_sequence=['#000000']*len(df))
        fig.add_hline(y=7, line_dash="dot",)
        fig.add_hline(y=21, line_dash="dot",)
        fig.add_hline(y=22, line_dash="dot",)
        #fig.update_layout(xaxis=dict(rangeselector=dict(buttons=list([dict(count=1,label="1m",step="month",stepmode="backward"),dict(count=6,label="6m",step="month",stepmode="backward"),dict(count=1,label="YTD",step="year",stepmode="todate"),dict(count=1,label="1y",step="year",stepmode="backward"),dict(step="all")])),rangeslider=dict(visible=True),type="date"))
        return style_figure(fig)
    
        
    return render(request, 'index.html', context=context)




def refresh_fitbit_data(access_token, refresh_token):
    client_id = "23PHFZ"
    client_secret = "public"
    authd_client = fitbit.Fitbit(client_id, client_secret, access_token=access_token, refresh_token=refresh_token)
    
    df = pd.DataFrame(columns=['date', 'start_time', 'end_time', 'end_minus_start_time', 'sleep_hours', 'stage_wake_hours', 'stage_light_hours', 'stage_rem_hours', 'stage_deep_hours', 'stages_total_hours'])
    days_data_avaliable = (datetime.datetime.now() - datetime.datetime(2024,5,27)).days + 1
    date_list = [datetime.datetime(2024,5,27) + datetime.timedelta(days=x) for x in range(days_data_avaliable)]
    for date in date_list:
        sleep_data = authd_client.sleep(date)
        print(date)
        if len(sleep_data['sleep']):
            stage_data = sleep_data['summary']['stages']
            sleep_duration_data = sleep_data['sleep']
            stages_df = pd.DataFrame(stage_data, index=[0])
            durration_df = pd.DataFrame(sleep_duration_data)
            durration_df['startTime'] = pd.to_datetime(durration_df['startTime'])
            durration_df['endTime'] = pd.to_datetime(durration_df['endTime'])
            init_df = pd.DataFrame([{
                    'date':date,
                    'start_time': durration_df['startTime'][0],
                    'end_time': durration_df['endTime'][0],
                    'end_minus_start_time': durration_df['endTime'][0] - durration_df['startTime'][0],
                    'sleep_hours': durration_df['timeInBed'][0]/60,
                    'stage_wake_hours': stages_df['wake'][0]/60,
                    'stage_light_hours': stages_df['light'][0]/60,
                    'stage_rem_hours': stages_df['rem'][0]/60,
                    'stage_deep_hours': stages_df['deep'][0]/60,
                    'stages_total_hours': stages_df['wake'][0]/60 + stages_df['light'][0]/60 + stages_df['rem'][0]/60 + stages_df['deep'][0]/60
                }])
            if len(df.index):    
                ddf = init_df
                df = pd.concat([df,ddf], axis=0)
            else:
                df = init_df
                
    print(df)
    df.reset_index(inplace=True)
    g, u = abel_gh_auth()
    filename = 'fitbit_sleep.csv'
    df.to_csv(filename, index=False)
    abel_put_file(g, u,  filename)
    os.remove(filename)  


def reload_sleep(request):
    tokens = gather_oauth()
    refresh_fitbit_data(tokens['access_token'], tokens['refresh_token'])
    return redirect('public:index')