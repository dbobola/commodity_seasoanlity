from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd
import plotly.graph_objs as go
import calendar, os, json
import requests

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
        config_data = read_config()
        start_month = config_data["start_month"]
        end_month = config_data["end_month"]
        lookback_years = config_data["duration"]
        exclusion = config_data["exclusion"]    
        current_year = config_data["current_year"]
        last_year = config_data["last_year"]
        asset = config_data["commodity"]

        assets_df = pd.read_csv("assets.csv", header=None)
        assets = assets_df[0].tolist()
        
        print(assets)

        try: 
            asset_name = asset.replace("/", "_")
            history_file = f'data/{asset_name}_history.csv'
            current_file = f'data/{asset_name}_current.csv'
              # Read data from CSV file
            df = pd.read_csv(history_file, parse_dates=['Date'], date_format='%m/%d/%y %H:%M')
            current_df = pd.read_csv(current_file, parse_dates=['Date'], date_format='%m/%d/%y %H:%M')


        except:
            asset = assets[0]
            config_data["commodity"] = asset
            asset_name = asset.replace("/", "_")
            history_file = f'data/{asset_name}_history.csv'
            current_file = f'data/{asset_name}_current.csv'
              # Read data from CSV file
            df = pd.read_csv(history_file, parse_dates=['Date'], date_format='%m/%d/%y %H:%M')
            current_df = pd.read_csv(current_file, parse_dates=['Date'], date_format='%m/%d/%y %H:%M')


      
        # List of years to exclude for certain exclusion types
        exclusion_years = [2020, 2016, 2012, 2008]
        # Dictionary mapping month numbers to month names
        month_names = {
            1: 'January',
            2: 'February',
            3: 'March',
            4: 'April',
            5: 'May',
            6: 'June',
            7: 'July',
            8: 'August',
            9: 'September',
            10: 'October',
            11: 'November',
            12: 'December'
        }


        # Adjust start and end month range
        if start_month == end_month:
            month_range = [start_month]
        elif end_month < start_month:
            config_data["start_month"] = 1
            write_config(config_data)
            month_range = range(1, start_month+1)
            return redirect(url_for('index'))
        else:
            month_range = range(start_month, end_month + 1)

        # Filter DataFrame based on month range
        filtered_df = pd.concat([df[df['Date'].dt.month == month] for month in month_range])
        filtered_current_df = pd.concat([current_df[current_df['Date'].dt.month == month] for month in month_range])
        
        # Adjust lookback years
        if lookback_years == 0:
            lookback_df = filtered_df
        else:
            lookback_df = filtered_df[filtered_df['Date'].dt.year >= (pd.Timestamp.now().year - lookback_years)]

        # Apply exclusion logic
        if exclusion == 'none':
            excluded_df = lookback_df
        elif exclusion == 'election':
            excluded_df = lookback_df[~lookback_df['Date'].dt.year.isin(exclusion_years)]
        elif exclusion == 'only-election':
            excluded_df = lookback_df[lookback_df['Date'].dt.year.isin(exclusion_years)]
        elif exclusion == '2020':
            excluded_df = lookback_df[lookback_df['Date'].dt.year != 2020]

        # Calculate the start and end dates for the selected month
        start_date = pd.Timestamp(year=2024, month=start_month, day=1)
        last_day_of_month = calendar.monthrange(start_date.year, end_month)[1]
        end_date = pd.Timestamp(year=start_date.year, month=end_month, day=last_day_of_month) + pd.Timedelta(minutes=660)

        # Create an empty DataFrame to store the results
        results_df = pd.DataFrame(columns=['Date', 'High', 'Low'])

        # Iterate through each day and time within the selected month
        #excluded_df =exclude_feb_29_data(excluded_df)
        current_date = start_date
        last_closing_data = None
        while current_date <= end_date:
            # Filter data for the current day and time
            
            filtered_data = excluded_df[(excluded_df['Date'].dt.month == current_date.month) &(excluded_df['Date'].dt.day == current_date.day) & (excluded_df['Date'].dt.hour == current_date.hour) & (excluded_df['Date'].dt.minute == current_date.minute)]
            current_data = filtered_current_df[(filtered_current_df['Date'].dt.month == current_date.month) &(filtered_current_df['Date'].dt.day == current_date.day) & (filtered_current_df['Date'].dt.hour == current_date.hour) & (filtered_current_df['Date'].dt.minute == current_date.minute)]
            #print(filtered_current_df)
            # Calculate the average high and low prices for the past N years
            if not filtered_data.empty:
                average_high = filtered_data['High'].mean()
                average_low = filtered_data['Low'].mean()
                half_price = filtered_data['Close'].mean()
                last_year_closing_price = filtered_data['Close'].iloc[-1]
                last_data = filtered_data
            else:
                average_high = last_data['High']
                average_low = last_data['Low']
                half_price = (average_high + average_low) / 2
                last_year_closing_price = last_data['Close']

            if not current_data.empty:
                current_year_closing_price = current_data['Close'].iloc[0]
                last_closing_data = current_year_closing_price
                
            else:
                current_year_closing_price = last_closing_data

                # Append results to the DataFrame if the date is not February 29th
            if not ((filtered_data['Date'].dt.month == 2) & (filtered_data['Date'].dt.day == 29)).any():
                results_df = pd.concat([results_df, pd.DataFrame({'Date': [current_date], 'High': [average_high], 'Low': [average_low], 'Half': [half_price], 'LastYearClose': [last_year_closing_price], 'CurrentYearClose': [current_year_closing_price]})])

            # Move to the next 30-minute interval
            current_date += pd.Timedelta(days=1)

        # Create line graphs for high, low, and half prices
        high_prices_graph = go.Scatter(x=results_df['Date'], y=results_df['High'], mode='lines', name='High Price', line=dict(color='blue', width=1))
        low_prices_graph = go.Scatter(x=results_df['Date'], y=results_df['Low'], mode='lines', name='Low Price', line=dict(color='blue', width=1), fill='tonexty', fillcolor='rgb(129, 207, 234)')
        half_prices_graph = go.Scatter(x=results_df['Date'], y=results_df['Half'], mode='lines', name='Close Price', line=dict(color='green', width=1))

        # Create line graphs for last year closing price and current year closing price
        last_year_close_graph = go.Scatter(x=results_df['Date'], y=results_df['LastYearClose'], mode='lines', name='Last Year Closing Price', line=dict(color='orange', width=1), yaxis='y2')
        current_year_close_graph = go.Scatter(x=results_df['Date'], y=results_df['CurrentYearClose'], mode='lines', name='Current Year Closing Price', line=dict(color='red', width=1), yaxis='y2')

        # Create layout
        start_month_name = month_names.get(start_month)
        end_month_name = month_names.get(end_month)
        if start_month == end_month:
            date_sentence = f"for the month of {start_month_name}"
        else:
            date_sentence = f"from the month of {start_month_name} to {end_month_name}"

        if exclusion == "election":
            exclusion_sentence = "election years"
        elif exclusion == "only-election":
            exclusion_sentence = "all years except election years"
        elif exclusion == "2020":
            exclusion_sentence = "year 2020"
        else:
            exclusion_sentence = "nothing"
        

        layout = go.Layout(
            title=f'{lookback_years} years Annual seasonality {date_sentence} excluding {exclusion_sentence}.',
            xaxis=dict(title='Date'),
            yaxis=dict(title='High, Low, Close Price'),  # Y1 axis for high, low, and close mean chart
            yaxis2=dict(title='Last Year, Current Year Closing Price', overlaying='y', side='right'),  # Y2 axis for last year and current year closing prices
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50),
            height=800,
            legend=dict(x=0, y=-0.2),
        )
        
        # Create figure
        graphs = [high_prices_graph, low_prices_graph, half_prices_graph ]
        if last_year:
            graphs.append(last_year_close_graph)

        if current_year:
            graphs.append(current_year_close_graph)

        

        config = {
            'toImageButtonOptions': {
                'format': 'png', # one of png, svg, jpeg, webp
                'filename': f'XAUUSD {lookback_years} years {date_sentence} excluding {exclusion_sentence}',
            
            }
            }
        fig = go.Figure(data=graphs, layout=layout)


        # Convert figure to HTML
        plot_div = fig.to_html(full_html=False, config=config)

        print("Selected Start Month:", start_month)
        print("Selected End Month:", end_month)
        print("Selected Duration:", lookback_years)
        print("Selected Exclusion:", exclusion)
        print("Show current Year : ", current_year)
        print("Show last Year : ", last_year)

        return render_template('index.html', plot_div=plot_div, config_data=config_data, assets=assets)
   
        

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        form_data = request.get_json()
        # Read existing config.json data
        config_data = read_config()
        config_data['commodity'] = form_data["commodity"]
        config_data['start_month'] = int(form_data["start_month"])
        config_data['end_month'] = int(form_data["end_month"])
        config_data['duration'] = int(form_data["duration"])
        config_data['exclusion'] = form_data["exclusion"]
        config_data['current_year'] = form_data["current_year"] if form_data["current_year"] else False
        config_data['last_year'] = form_data["last_year"] if form_data["last_year"] else False
        write_config(config_data)

        response = {'status': 'success', 'message': 'Form data received and config updated successfully'}
        return jsonify(response)

    except:
        response = {'status': 'error', 'message': 'Error processing form data'}
        return jsonify(response)
    

@app.route('/add_asset', methods=['POST'])
def add_asset():
    try:
        form_data = request.get_json()
        asset = form_data["asset"]
        assets_df = pd.read_csv("assets.csv", header=None)
        assets = assets_df[0].tolist()
        get_all_data(asset)
        print(assets)
        if asset in assets:
            response = {'status': 'exists', 'message': 'Asset already exists'}
            return jsonify(response)
        else:
            assets.append(asset)
            assets = list(set(assets))
            # Convert the list to a DataFrame
            assets_df = pd.DataFrame(assets)
            
            # Write the updated DataFrame back to the CSV file
            assets_df.to_csv("assets.csv", header=False, index=False)
            print(assets)

            config_data = read_config()
            config_data["commodity"] = asset
            write_config(config_data)
            response = {'status': 'success', 'message': 'Asset added successfully'}
            return jsonify(response)
    except:
        response = {'status': 'error', 'message': 'Error adding asset'}
        return jsonify(response)


@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        get_current_data()
        response = {'status': 'success', 'message': 'Data updated successfully'}
        return jsonify(response)
    except:
        response = {'status': 'error', 'message': 'Error updating data'}
        return jsonify(response)

def get_current_data():
    assets_df = pd.read_csv("assets.csv", header=None)
    assets = assets_df[0].tolist()
    for asset in assets:
        try:
            asset_name = asset.replace("/", "_")
            current_api_url = f"https://api.twelvedata.com/time_series?start_date=2024-01-01&symbol={asset}&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
            current_file = f'data/{asset_name}_current.csv'
            convert_to_daily_data_format(current_api_url, current_file )
        except:
            pass


def get_all_data(asset):
    history_api_url = f"https://api.twelvedata.com/time_series?start_date=2009-01-01&end_date=2023-12-31&symbol={asset}&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
    asset_name = asset.replace("/", "_")
    history_file = f'data/{asset_name}_history.csv'
    convert_to_daily_data_format(history_api_url, history_file)
    current_api_url = f"https://api.twelvedata.com/time_series?start_date=2024-01-01&symbol={asset}&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
    current_file = f'data/{asset_name}_current.csv'
    convert_to_daily_data_format(current_api_url, current_file )

def convert_to_daily_data_format(api_url, output_csv_path):
    response = requests.get(api_url)
    
    if response.status_code == 200:
        data = response.json()
        values = data.get('values', [])
        df = pd.DataFrame(values)
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'datetime': 'Date'}, inplace=True)
        
        # Convert Date column to datetime format
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date')
        
        # Set Date as index for resampling
        df.set_index('Date', inplace=True)
        
        # Resample to fill missing dates and forward fill the values
        df = df.resample('D').ffill()
        
        # Reset index to get Date back as a column
        df.reset_index(inplace=True)
        
    
        
        # Convert Date column to the desired string format
        df['Date'] = df['Date'].dt.strftime('%m/%d/%y %H:%M')
        
        # Reorder the columns
        df = df[['Open', 'High', 'Low', 'Close', 'Date']]
        
        # Save to CSV
        df.to_csv(output_csv_path, index=False)
        
        print("Data successfully converted and saved to", output_csv_path)
    else:
        print("Failed to retrieve data from the API:", response.status_code)


def extract_data_from_csv(input_csv_path, output_csv_path):
    # Read data from input CSV file
    df = pd.read_csv(input_csv_path, parse_dates=['Date'], date_parser=lambda x: pd.to_datetime(x, format='%m/%d/%y %H:%M'))

    # Filter data starting from the year 2024
    df_2024 = df[df['Date'].dt.year >= 2024]

    # Save filtered data to another CSV file
    df_2024.to_csv(output_csv_path, index=False)


def convert_to_daily_data(input_csv_path, output_csv_path):
    # Read the CSV file
    df = pd.read_csv(input_csv_path, parse_dates=['Date'])
    
    # Set the 'Date' column as the index
    df.set_index('Date', inplace=True)
    
    # Resample the data to daily frequency and aggregate
    daily_df = df.resample('D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    })
    daily_df['Date'] = daily_df.index.strftime('%m/%d/%y %H:%M')
    daily_df.to_csv(output_csv_path, index=False)

def read_config():
    config_path = os.path.join(os.path.dirname(__file__), './','data.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return config_data

def write_config(config_data):
    config_path = os.path.join(os.path.dirname(__file__), './','data.json')
    with open(config_path, 'w') as config_file:
        json.dump(config_data, config_file, indent=4)

def exclude_feb_29_data(df):    
    # Check if February 29th exists in the data
    feb_29_exists = any((df['Date'].dt.month == 2) & (df['Date'].dt.day == 29))
    
    # If February 29th doesn't exist, use data from February 28th instead
    if not feb_29_exists:
        # Filter out February 28th data for leap years
        df = df[~((df['Date'].dt.month == 2) & (df['Date'].dt.day == 28) & (df['Date'].dt.year % 4 == 0))]
            
    return df

if __name__ == '__main__':
    app.run(debug=True)
