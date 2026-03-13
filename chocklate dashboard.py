# ultimate_chocolate_dashboard_final.py

import pandas as pd
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from sqlalchemy import create_engine
from datetime import datetime

# -------------------------------
# 1️⃣ Connect to SQL Server Database using SQLAlchemy
# -------------------------------
server = 'localhost'
database = 'chocklate'

engine = create_engine(
    f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)

query = "SELECT * FROM FCT_Sales"
df = pd.read_sql(query, engine)

# -------------------------------
# 2️⃣ Preprocess Data
# -------------------------------
df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
df['Boxes_Shipped'] = pd.to_numeric(df['Boxes_Shipped'], errors='coerce')
df['Date'] = pd.to_datetime(df['DateKey'], format='%Y%m%d', errors='coerce')
df['Month'] = df['Date'].dt.to_period('M')

# -------------------------------
# 3️⃣ Initialize Dash App
# -------------------------------
app = Dash(__name__)
app.title = "🍫 Ultimate Chocolate Dashboard"

# -------------------------------
# 4️⃣ Helper: Create Charts
# -------------------------------
def create_charts(filtered_df):
    # Sales by Country
    sales_by_country = filtered_df.groupby("Country")["Amount"].sum().reset_index()
    sales_by_country = sales_by_country.sort_values(by="Amount", ascending=False)
    fig_country = px.bar(
        sales_by_country, x="Country", y="Amount",
        title="🌎 Sales by Country", text="Amount",
        color="Amount", color_continuous_scale='Viridis'
    )

    # Sales by Product
    sales_by_product = filtered_df.groupby("Product")["Amount"].sum().reset_index()
    fig_product = px.pie(
        sales_by_product, names="Product", values="Amount",
        title="🍫 Sales Distribution by Product", hole=0.4
    )

    # Monthly Sales Trend
    monthly_sales = filtered_df.groupby(filtered_df['Date'].dt.to_period('M'))['Amount'].sum().reset_index()
    monthly_sales['Date'] = monthly_sales['Date'].dt.to_timestamp()
    fig_trend = px.line(
        monthly_sales, x='Date', y='Amount',
        title="📈 Monthly Sales Trend", markers=True
    )

    # Top 5 Products
    top_products = filtered_df.groupby('Product')['Amount'].sum().reset_index().sort_values(by='Amount', ascending=True).tail(5)
    fig_top_products = px.bar(
        top_products, x='Amount', y='Product', orientation='h',
        title="🏆 Top 5 Products", text='Amount',
        color='Amount', color_continuous_scale='Cividis'
    )

    return fig_country, fig_product, fig_trend, fig_top_products

# -------------------------------
# 5️⃣ App Layout
# -------------------------------
app.layout = html.Div([
    html.H1("🍫 Ultimate Chocolate Dashboard", style={'textAlign': 'center'}),

    # Filters
    html.Div([
        html.Div([
            html.Label("Select Country:"),
            dcc.Dropdown(
                id='country-dropdown',
                options=[{'label': c, 'value': c} for c in sorted(df['Country'].unique())],
                value=list(df['Country'].unique()),
                multi=True
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),

        html.Div([
            html.Label("Select Product:"),
            dcc.Dropdown(
                id='product-dropdown',
                multi=True
            )
        ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%'}),

        html.Div([
            html.Label("Select Date Range:"),
            dcc.DatePickerRange(
                id='date-range',
                min_date_allowed=df['Date'].min(),
                max_date_allowed=df['Date'].max(),
                start_date=df['Date'].min(),
                end_date=df['Date'].max()
            )
        ], style={'width': '35%', 'display': 'inline-block'}),
    ], style={'marginBottom': '25px'}),

    # KPI Cards
    html.Div(id='kpi-cards', style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '25px'}),

    # Charts
    html.Div([
        html.Div([dcc.Graph(id='bar-country')], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='pie-product')], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%'}),
        html.Div([dcc.Graph(id='line-trend')], style={'width': '100%', 'marginTop': '20px'}),
        html.Div([dcc.Graph(id='top-products')], style={'width': '100%', 'marginTop': '20px'}),
    ]),

    # Download CSV
    html.Div([
        html.Button("Download Filtered Data", id="download-btn"),
        dcc.Download(id="download-data")
    ], style={'textAlign': 'center', 'marginTop': '20px'})
], style={'fontFamily': 'Arial, sans-serif'})

# -------------------------------
# 6️⃣ Callbacks
# -------------------------------
@app.callback(
    Output('product-dropdown', 'options'),
    Output('product-dropdown', 'value'),
    Input('country-dropdown', 'value')
)
def update_products(selected_countries):
    filtered = df[df['Country'].isin(selected_countries)] if selected_countries else df
    options = [{'label': p, 'value': p} for p in sorted(filtered['Product'].unique())]
    values = [p['value'] for p in options]
    return options, values

@app.callback(
    Output('bar-country', 'figure'),
    Output('pie-product', 'figure'),
    Output('line-trend', 'figure'),
    Output('top-products', 'figure'),
    Output('kpi-cards', 'children'),
    Input('country-dropdown', 'value'),
    Input('product-dropdown', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date')
)
def update_dashboard(selected_countries, selected_products, start_date, end_date):
    filtered_df = df.copy()
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
    if selected_products:
        filtered_df = filtered_df[filtered_df['Product'].isin(selected_products)]
    filtered_df = filtered_df[(filtered_df['Date'] >= pd.to_datetime(start_date)) &
                              (filtered_df['Date'] <= pd.to_datetime(end_date))]

    fig_country, fig_product, fig_trend, fig_top_products = create_charts(filtered_df)

    # KPI Cards
    total_sales = filtered_df['Amount'].sum()
    total_boxes = filtered_df['Boxes_Shipped'].sum()
    max_sale = filtered_df['Amount'].max()
    avg_sale = filtered_df['Amount'].mean()
    top_product = filtered_df.groupby('Product')['Amount'].sum().idxmax()

    kpi_children = [
        html.Div([html.H3("Total Sales"), html.P(f"${total_sales:,.2f}", style={'color': 'green', 'fontSize': '22px'})],
                 style={'border': '2px solid #ccc', 'padding': '10px', 'width': '18%', 'textAlign': 'center', 'borderRadius': '8px'}),
        html.Div([html.H3("Total Boxes Shipped"), html.P(f"{total_boxes:,}", style={'color': 'orange', 'fontSize': '22px'})],
                 style={'border': '2px solid #ccc', 'padding': '10px', 'width': '18%', 'textAlign': 'center', 'borderRadius': '8px'}),
        html.Div([html.H3("Max Sale"), html.P(f"${max_sale:,.2f}", style={'color': 'blue', 'fontSize': '22px'})],
                 style={'border': '2px solid #ccc', 'padding': '10px', 'width': '18%', 'textAlign': 'center', 'borderRadius': '8px'}),
        html.Div([html.H3("Average Sale"), html.P(f"${avg_sale:,.2f}", style={'color': 'purple', 'fontSize': '22px'})],
                 style={'border': '2px solid #ccc', 'padding': '10px', 'width': '18%', 'textAlign': 'center', 'borderRadius': '8px'}),
        html.Div([html.H3("Top Product"), html.P(f"{top_product}", style={'color': 'red', 'fontSize': '22px'})],
                 style={'border': '2px solid #ccc', 'padding': '10px', 'width': '18%', 'textAlign': 'center', 'borderRadius': '8px'})
    ]

    return fig_country, fig_product, fig_trend, fig_top_products, kpi_children

@app.callback(
    Output("download-data", "data"),
    Input("download-btn", "n_clicks"),
    Input('country-dropdown', 'value'),
    Input('product-dropdown', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    prevent_initial_call=True
)
def download_filtered(n_clicks, selected_countries, selected_products, start_date, end_date):
    filtered_df = df.copy()
    if selected_countries:
        filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
    if selected_products:
        filtered_df = filtered_df[filtered_df['Product'].isin(selected_products)]
    filtered_df = filtered_df[(filtered_df['Date'] >= pd.to_datetime(start_date)) &
                              (filtered_df['Date'] <= pd.to_datetime(end_date))]
    return dcc.send_data_frame(filtered_df.to_csv, f"filtered_chocolate_sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# -------------------------------
# 7️⃣ Run App
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)