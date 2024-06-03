import pandas as pd
import requests

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




def get_historical_data():
    assets = ["XAU/USD", "XAG/USD", "WTI/USD", "GBP/USD", "BTC/USD"]
    for asset in assets:
        history_api_url = f"https://api.twelvedata.com/time_series?start_date=2009-01-01&end_date=2023-12-31&symbol={asset}&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
        asset_name = asset.replace("/", "_")
        history_file = f'data/{asset_name}_history.csv'
        convert_to_daily_data_format(history_api_url, history_file)
        current_api_url = f"https://api.twelvedata.com/time_series?start_date=2024-01-01&symbol={asset}&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
        current_file = f'data/{asset_name}_current.csv'
        convert_to_daily_data_format(current_api_url, current_file )

get_historical_data()