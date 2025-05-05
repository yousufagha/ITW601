# INSTALL THESE LIBRARIES IN TERMINAL:
# pip install dash dash-bootstrap-components dash-table pandas plotly

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, dash_table
import pandas as pd
import numpy as np
import plotly.express as px

# Load dataset
# df = pd.read_csv("enriched_jora_jobs_9000.csv")
# df = pd.read_csv("cleaned_data.csv")
df = pd.read_csv("cleaned_data_1.csv")

# Handle Experience column
def parse_experience(val):
    if pd.isna(val):
        return np.nan
    try:
        if '-' in str(val):
            return float(str(val).split('-')[0])
        return float(str(val))
    except:
        return np.nan

df['ParsedExperience'] = df['Experience'].apply(parse_experience)

# Geolocation data for key cities in Australia
city_coords = pd.DataFrame({
    'City': ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Canberra'],
    'Latitude': [-33.8698, -37.8142, -27.4690, -31.9559, -34.9282, -35.2976],
    'Longitude': [151.2083, 144.9632, 153.0235, 115.8606, 138.5999, 149.1013]
})

# Count unique skills per city
skills_data = df[['City', 'Skills']].dropna()
skills_data['Skills'] = skills_data['Skills'].str.split(',')
skills_data = skills_data.explode('Skills')
skills_data['Skills'] = skills_data['Skills'].str.strip()
skill_counts = skills_data.groupby('City')['Skills'].nunique().reset_index(name='UniqueSkills')

# Merge with coordinates
skills_map_df = pd.merge(skill_counts, city_coords, on='City', how='inner')

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Job Listings Dashboard"
server = app.server

# Sidebar Filters 
sidebar = dbc.Col([
    html.H4("Filters", className="pt-3"),
    html.Hr(),

    dbc.Label("State"),
    dcc.Dropdown(
        id='state-filter',
        options=[{'label': state, 'value': state} for state in df['State'].dropna().unique()],
        multi=True,
        placeholder="Select State(s)"
    ),

    dbc.Label("City"),
    dcc.Dropdown(
        id='city-filter',
        options=[{'label': city, 'value': city} for city in df['City'].dropna().unique()],
        multi=True,
        placeholder="Select City(s)"
    ),
    
], width=2, style={"backgroundColor": "#f8f9fa", "height": "100vh", "padding": "20px", "position": "fixed"})

# KPI Cards
def kpi_card(title, value):
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="card-title"),
            html.H4(value, className="card-text")
        ])
    ], className="m-1")  # Reduced margin for better alignment

# Map Tab Layout
map_tab = dbc.Tab(label="Skill Map", children=[
    dcc.Graph(
        figure=px.scatter_map(
            skills_map_df,
            lat="Latitude",
            lon="Longitude",
            size="UniqueSkills",
            color="UniqueSkills",
            hover_name="City",
            zoom=3.8,
            map_style="open-street-map",
            title="Unique Skill Distribution by City"
        )
    )
])

# Main Content with Tabs
content = dbc.Col([
    html.H2("Job Listings Overview", className="mb-4"),
    dbc.Row([
        dbc.Col(kpi_card("Total Jobs", df.shape[0]), width=3),
        dbc.Col(kpi_card("Top State", df['State'].mode()[0]), width=3),
        dbc.Col(kpi_card("Top City", df['City'].mode()[0]), width=3),
        dbc.Col(kpi_card("Avg Experience", f"{df['ParsedExperience'].dropna().mean():.1f} yrs"), width=3),
    ]),
    html.Hr(),

    dcc.Tabs([
        dbc.Tab(label="Dashboard", children=[
            html.H5("Data Visualizations"),
            dbc.Row([
                dbc.Col(dcc.Graph(id='skills-treemap'), width=12),
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='exp-distribution'), width=6),
                dbc.Col(dcc.Graph(id='jobs-by-city'), width=6),
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='jobs-by-state'), width=6),
                dbc.Col(dcc.Graph(id='jobs-by-company'), width=6),
            ]),
            html.Hr(),
            html.H5("All Job Listings"),
            dash_table.DataTable(
                id='job-table',
                columns=[{"name": col, "id": col} for col in ["Title", "Company", "City", "State", "Experience"]],
                data=df.to_dict('records'),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left"},
            )
        ]),
        map_tab
    ])
], width={"size": 10, "offset": 2}, style={"padding": "20px"})

# Layout
app.layout = dbc.Container([
    dbc.Row([sidebar, content])
], fluid=True)

# Callback: Table Filter 
@app.callback(
    Output('job-table', 'data'),
    [Input('state-filter', 'value'),
     Input('city-filter', 'value')]
)
def update_table(selected_states, selected_cities):
    filtered_df = df.copy()
    if selected_states:
        filtered_df = filtered_df[filtered_df['State'].isin(selected_states)]
    if selected_cities:
        filtered_df = filtered_df[filtered_df['City'].isin(selected_cities)]
    return filtered_df.to_dict('records')

# Callback: Graph Updates 
@app.callback(
    [Output('exp-distribution', 'figure'),
     Output('jobs-by-city', 'figure'),
     Output('jobs-by-state', 'figure'),
     Output('jobs-by-company', 'figure'),
     Output('skills-treemap', 'figure')],
    [Input('state-filter', 'value'),
     Input('city-filter', 'value')]
)
def update_visualizations(selected_states, selected_cities):
    filtered_df = df.copy()
    if selected_states:
        filtered_df = filtered_df[filtered_df['State'].isin(selected_states)]
    if selected_cities:
        filtered_df = filtered_df[filtered_df['City'].isin(selected_cities)]


    # Experience Distribution
    exp_dist_fig = px.histogram(filtered_df, x='ParsedExperience', nbins=20, title="Experience Distribution")
    exp_dist_fig.update_layout(xaxis_title="Experience", yaxis_title="Count")

    # Jobs by City
    city_counts = filtered_df['City'].value_counts().reset_index()
    city_counts.columns = ['City', 'Count']
    jobs_by_city_fig = px.bar(city_counts, x='City', y='Count', title="Jobs by City")

    # Jobs by State
    state_counts = filtered_df['State'].value_counts().reset_index()
    state_counts.columns = ['State', 'Count']
    jobs_by_state_fig = px.bar(state_counts, x='State', y='Count', title="Jobs by State")

    # Jobs by Company
    company_counts = filtered_df['Company'].value_counts().reset_index()
    company_counts.columns = ['Company', 'Count']
    jobs_by_company_fig = px.bar(company_counts, x='Company', y='Count', title="Jobs by Company")
    filtered_skills = filtered_df[['City', 'Skills']].dropna()
    filtered_skills['Skills'] = filtered_skills['Skills'].str.split(',')
    exploded_skills = filtered_skills.explode('Skills')
    exploded_skills['Skills'] = exploded_skills['Skills'].str.strip()
    pivot_treemap = exploded_skills.groupby(['City', 'Skills']).size().reset_index(name='Count')

    skills_treemap_fig = px.treemap(
        pivot_treemap,
        path=['City', 'Skills'],
        values='Count',
        title='Skill Distribution by City'
    )

    return exp_dist_fig, jobs_by_city_fig, jobs_by_state_fig, jobs_by_company_fig, skills_treemap_fig

# Run App
if __name__ == "__main__":
    app.run(debug=True)