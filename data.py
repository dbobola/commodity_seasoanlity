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
    # Make the API call
    response = requests.get(api_url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Extract the values from the response
        values = data.get('values', [])
        print(values)
        
        # Create a DataFrame from the extracted values
        df = pd.DataFrame(values)
        
        # Rename columns
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'datetime': 'Date'}, inplace=True)
        
        # Convert Date column to datetime format
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Sort by date in ascending order
        df = df.sort_values(by='Date')
        
        # Convert date format
        df['Date'] = df['Date'].dt.strftime('%m/%d/%y %H:%M')
        
        # Save to CSV
        df.to_csv(output_csv_path, index=False)
        
        print("Data successfully converted and saved to", output_csv_path)
    else:
        print("Failed to retrieve data from the API:", response.status_code)

api_url = "https://api.twelvedata.com/time_series?start_date=2024-01-01&symbol=xau/usd&interval=1day&apikey=d8dfab6c3fce444e877032ef320bc4bb"
convert_to_daily_data_format(api_url,'data/current_data_1d.csv', )
