import pandas as pd
import datetime
from pandas import DataFrame
from pandasql import sqldf

loc = locals()

def calculate_average_ticker_price(prices: {}, total_quantity: float) -> float:
    """
    :param prices: a list of price * quantity needed to calculate the average price of each stock
    :param total_quantity: the total amount of the stock held, required to calculate the average price per stock.
    :return: the average price for that particular ticker stock given
    1. the different purchase price
    2. the different quantities purchased
    """

    if total_quantity > 0:
        total_price = sum(prices)

        return total_price / total_quantity


def strip_action(action: str) -> str:
    """
    removes whitespace and changes all characters to lower case
    :param action: the name of the action taken on a position
    :return: the input string minus the above mentioned
    """

    action = action.replace(" ", "")
    action = action.casefold()

    return action


def profit_from_sale(ticker_number: str, sale_price: float, quantity: float, action: str) -> float:
    """
    Calculates the amount of profit/loss realised from a sale of a stock.
    :param ticker_number: ticker name of the stock
    :param sale_price: sale/cover price of the stock
    :param quantity: the number of stock sold/bought.
    :param action: is this position a "longsell" or a "shortcover"
    :return: profit/loss of the action taken
    """

    if action == "longsell":

        profit_or_loss = (sale_price - price_list[ticker_number]) * quantity

        return profit_or_loss

    elif action == "shortcover":

        profit_or_loss = (price_list[ticker_number] - sale_price) * quantity

        return profit_or_loss


def date_remove_time(date: datetime) -> datetime:
    """
    converts a datetime format of %Y-%m-%d %H:%M:%S.%f to %d/%m/%Y
    :param date: date
    :return: a cleaner date without the above mentioned
    """

    return datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S.%f').strftime('%d/%m/%Y')


myportfolio = pd.read_excel('portfoliodataset.xlsx', index_col=False)

# PANDAS SETTINGS
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('colheader_justify', 'center')
pd.set_option('display.float_format', lambda x: '%.2f' % x)

net_position_query = "SELECT mp.Ticker as Ticker,  " \
                     "(SUM(IIF (mp.Action LIKE '%Long Buy%', mp.Quantity, " \
                     "IIF(mp.Action LIKE '%Long Sell%', -1 * mp.Quantity, " \
                     "IIF(mp.Action LIKE '%Short Sell%', 1 * mp.Quantity, " \
                     "IIF(mp.Action LIKE '%Short Cover%', mp.Quantity, " \
                     "IIF(mp.Action LIKE '%Subscription%', mp.Quantity, 0)" \
                     ")))))) as [Current Quantity]," \
                     "max(mp.date) as [latest activity] " \
                     "FROM myportfolio AS mp " \
                     "" \
                     "GROUP BY mp.Ticker " \
                     "ORDER BY mp.Date ASC" \

# ANALYSE PRICE OF EACH SHARE HOLDING
# PNL Query
base_query = "SELECT Ticker, Price, Action, Quantity, Date, " \
             "(Commissions + Stamp + Levy + CCASS + [trading fees]) as [Position Cost] " \
             "FROM myportfolio as mp " \
             "ORDER BY Ticker, Date ASC" \

base_query = sqldf(base_query, loc)

base_query = DataFrame(base_query, columns=['Ticker', 'Date', 'Price', 'Quantity', 'Position Cost', 'Action']).values.tolist()

current_ticker = 0
total_quantity = 0
prices = []

price_list = {}

for i, trade in enumerate(base_query):

    # Ticker
    ticker_number = trade[0]
    price = trade[2]
    quantity = trade[3]
    position_cost = trade[4]
    action = strip_action(trade[5])

    if i == 0:
        current_ticker = ticker_number

    if current_ticker == ticker_number:
        # WORK OUT THE AVERAGE PRICE OF THE TICKER

        if action == "longbuy" or action == "shortsell":

            prices.append((price * abs(quantity)) - position_cost)

            total_quantity += abs(quantity)

    # Start on another ticker
    else:
        # Calculate previous ticker price
        average_price_for_ticker = calculate_average_ticker_price(prices, total_quantity)

        price_list[current_ticker] = average_price_for_ticker

        current_ticker = trade[0]
        total_quantity = 0
        prices.clear()

        if action == "longbuy" or action == "shortsell":

            price = trade[2]
            quantity = trade[3]
            prices.append((price * abs(quantity)) - position_cost)

            total_quantity += abs(quantity)

# LATEST SELL PRICE

sale_price_list = {}
sale_current_ticker = 0
price = 0

for i, sale_price in enumerate(reversed(base_query)):

    ticker_number = sale_price[0]
    stock_price = sale_price[2]
    action = sale_price[5]

    if i == 0:
        sale_current_ticker = ticker_number

    if strip_action(action) == "longsell" or "longcover":

        # print("Date: {} Ticker: {} price: {}".format(sale_price[1], ticker_number, stock_price))

        price = stock_price

        if ticker_number != sale_current_ticker:

            sale_price_list[ticker_number] = price

            price = 0
            sale_current_ticker = ticker_number

# CAN REMOVE
# # THIS IS THE UP TO DATE LIST OF YOUR AVERAGE PRICES FOR EACH STOCK NAME

# 1. CURRENT POSITIONS - Analyses

net_position_query = sqldf(net_position_query, loc)

net_position_query = DataFrame(net_position_query,
                               columns=['Ticker', 'latest activity', 'Current Quantity']).values.tolist()

net_positions_updated_list = []
net_unrealised_list = []

# portfolio value at market price.
portfolio_total_value = 0

for position in net_position_query:

    ticker_number = position[0]
    latest_activity = date_remove_time(position[1])
    quantity = position[2]

    if quantity > 0 and ticker_number != 'HKD':

        position_value = quantity * price_list[ticker_number]

        portfolio_total_value += position_value

        # print("position value: {}".format(position_value))

        # Portfolio at average purchased price
        net_positions_updated_list.append([ticker_number, position_value, latest_activity])

        # Portfolio average purchased price against latest strike price.
        unrealised_pnl = quantity * (price_list[ticker_number] - sale_price_list[ticker_number])

        if unrealised_pnl == 0:
            net_unrealised_list.append([ticker_number, "INADEQUATE PRICE INFO", latest_activity])
        else:
            net_unrealised_list.append([ticker_number, unrealised_pnl, latest_activity])


# KEEP THIS for later
net_position_df = pd.DataFrame(net_positions_updated_list, columns=['Ticker', 'Position Value', 'Latest Activity'])

print("Current Positions: \n {}".format(net_position_df))
print("\n")
print("Portfolio total value: {} HKD".format(round(portfolio_total_value, 2)))
print("*"*40)
print("\n")

net_unrealised_df = pd.DataFrame(net_unrealised_list, columns=['Ticker', 'Unrealised', 'Latest Activity'])

# 2. REALISED PROFITS/ COMPLETED TRANSACTIONS
profit_loss = 0
profit_loss_list = []
subscription = 0

# Work out your profit and loss for all your realised transactions

for trade in base_query:

    ticker_number = trade[0]
    trade_date = date_remove_time(trade[1])
    sale_price = trade[2]
    sale_quantity = trade[3]
    position_cost = trade[4]
    action = strip_action(trade[5])

    if action == "longsell":

        profit_or_loss_before_cost = profit_from_sale(ticker_number, sale_price, quantity, "longsell")
        profit_or_loss_after_cost = profit_or_loss_before_cost - position_cost

        profit_loss += profit_or_loss_after_cost

        profit_loss_list.append(
            [trade_date, ticker_number, "LONG SELL", sale_price, sale_quantity,profit_or_loss_before_cost, position_cost, round(profit_or_loss_after_cost, 2)])

    elif action == "shortcover":

        profit_or_loss_before_cost = profit_from_sale(ticker_number, sale_price, quantity, "shortcover")
        profit_or_loss_after_cost = profit_or_loss_before_cost - position_cost

        profit_loss += profit_or_loss_after_cost

        profit_loss_list.append(
            [trade_date, ticker_number, "SHORT COVER", sale_price, sale_quantity,profit_or_loss_before_cost, position_cost, round(profit_or_loss_after_cost, 2)])

    elif action == "subscription":

        subscription = sale_price * sale_quantity

profit_loss_list_df = pd.DataFrame(profit_loss_list,
                                columns=['Date', 'Ticker', 'Action', 'Price', 'Quantity', 'Profit Before Cost', 'Cost of Position', 'Profit/Loss'])

print("Realised Profit and loss: \n{}".format(profit_loss_list_df))
print("\n")
print("Total Profit and Loss: {} HKD".format(round(profit_loss, 2)))
print("*"*40)

print("\n")

available_funds = profit_loss + subscription

print("Unrealised Profit and loss: \n{} ".format(net_unrealised_df))
print("*"*40)
print("\n")
print("Available funds: {} HKD".format(round(available_funds,2)))

# UNREALISED PROFITS

while True:
    export = input("would you like to export to Excel? Y/N ")

    if export.casefold() == "y":

        print("Exporting to Excel...")

        with pd.ExcelWriter('Report.xlsx') as writer:

            net_position_df.to_excel(writer, sheet_name="Current Positions", index= False)
            profit_loss_list_df.to_excel(writer, sheet_name="Realised Profit and Loss", index= False)
            net_unrealised_df.to_excel(writer, sheet_name="Unrealised Profit and Loss", index= False)

        break

    elif export.casefold() == "n":

        break
