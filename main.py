import streamlit as st
import pandas as pd
import yfinance as yf
from openai import OpenAI
import os
from dotenv import load_dotenv

# Set up OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to generate explanations using GPT
def generate_explanation(symbol, quantity_change):
    if quantity_change > 0:
        action = f"buy {quantity_change} more shares of {symbol}"
    elif quantity_change < 0:
        action = f"sell {-quantity_change} shares of {symbol}"
    else:
        action = f"hold your current position in {symbol}"

    prompt = f"As a financial advisor, explain why the client should {action} to rebalance their portfolio."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional financial advisor providing portfolio rebalancing advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        explanation = response.choices[0].message.content.strip()
        return explanation
    except Exception as e:
        return f"Error generating explanation: {e}"

# Define a class for stock holdings
class StockHolding:
    def __init__(self, symbol, quantity):
        self.symbol = symbol
        self.quantity = quantity
        self.current_price = 0
        self.total_value = 0
        self.allocation_percentage = 0
        self.ideal_allocation = 0
        self.allocation_difference = 0
        self.value_difference = 0
        self.quantity_change = 0
        self.explanation = ''
    
    def update_price(self):
        data = yf.Ticker(self.symbol).history(period='1d')
        if data.empty:
            raise ValueError(f"Could not fetch data for symbol {self.symbol}")
        self.current_price = data['Close'].iloc[-1]
        self.total_value = self.current_price * self.quantity
    
    def calculate_allocation(self, total_portfolio_value, ideal_allocation):
        self.allocation_percentage = (self.total_value / total_portfolio_value) * 100
        self.ideal_allocation = ideal_allocation
        self.allocation_difference = self.ideal_allocation - self.allocation_percentage
        self.value_difference = (self.allocation_difference / 100) * total_portfolio_value
        self.quantity_change = int(round(self.value_difference / self.current_price))
    
    def generate_explanation(self):
        self.explanation = generate_explanation(self.symbol, self.quantity_change)

# Define a class for the portfolio
class Portfolio:
    def __init__(self, holdings):
        self.holdings = holdings
        self.total_value = 0
    
    def update_holdings(self):
        self.total_value = 0
        for holding in self.holdings:
            holding.update_price()
            self.total_value += holding.total_value
    
    def analyze(self):
        ideal_allocation = 100 / len(self.holdings)
        for holding in self.holdings:
            holding.calculate_allocation(self.total_value, ideal_allocation)
            holding.generate_explanation()

# Streamlit app layout
def main():
    st.title('AI-Powered Stock Portfolio Rebalancing Advisor')

    st.write('Enter your current stock holdings below:')

    # Add some sample data and explanation
    st.write("""
    Example input:
    - Symbols: AAPL, MSFT, GOOGL
    - Quantities: 10, 5, 8
    """)

    symbols_input = st.text_area('Stock Symbols (comma-separated)', 'AAPL, MSFT, GOOGL')
    quantities_input = st.text_area('Quantities (comma-separated)', '10, 5, 8')

    submit_button = st.button('Analyze Portfolio')

    if submit_button:
        try:
            symbols = [symbol.strip().upper() for symbol in symbols_input.split(',')]
            quantities = [int(q.strip()) for q in quantities_input.split(',')]

            if len(symbols) != len(quantities):
                st.error('The number of symbols and quantities must match.')
                st.stop()
            
            # Create StockHolding objects
            holdings = [StockHolding(symbols[i], quantities[i]) for i in range(len(symbols))]

            # Create a Portfolio object
            portfolio = Portfolio(holdings)
            
            with st.spinner('Fetching current market data...'):
                portfolio.update_holdings()
            
            with st.spinner('Analyzing portfolio and generating recommendations...'):
                portfolio.analyze()

            # Prepare data for display
            portfolio_data = {
                'Symbol': [],
                'Quantity': [],
                'Current Price': [],
                'Total Value': [],
                'Current Allocation (%)': [],
                'Target Allocation (%)': [],
                'Recommended Change': [],
            }

            for holding in portfolio.holdings:
                portfolio_data['Symbol'].append(holding.symbol)
                portfolio_data['Quantity'].append(holding.quantity)
                portfolio_data['Current Price'].append(f"${holding.current_price:.2f}")
                portfolio_data['Total Value'].append(f"${holding.total_value:.2f}")
                portfolio_data['Current Allocation (%)'].append(f"{holding.allocation_percentage:.2f}%")
                portfolio_data['Target Allocation (%)'].append(f"{holding.ideal_allocation:.2f}%")
                portfolio_data['Recommended Change'].append(holding.quantity_change)

            portfolio_df = pd.DataFrame(portfolio_data)
            
            st.subheader('Portfolio Analysis')
            st.dataframe(portfolio_df)
            st.write(f'Total Portfolio Value: ${portfolio.total_value:.2f}')

            # Display explanations
            st.subheader('Rebalancing Recommendations')
            for holding in portfolio.holdings:
                st.markdown(f"**{holding.symbol}**")
                st.write(holding.explanation)
                st.write("---")
            
        except ValueError as e:
            st.error(f'Error processing input: {e}')
            st.stop()
        except Exception as e:
            st.error(f'An unexpected error occurred: {e}')
            st.stop()

if __name__ == "__main__":
    main()