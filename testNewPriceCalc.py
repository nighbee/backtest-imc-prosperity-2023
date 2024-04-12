from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
from collections import deque

class Trader:
    POSITION_LIMIT = 20  # The maximum absolute value of the position
    STOP_LOSS_THRESHOLD = 9500  # Set a stop-loss threshold for AMETHYSTS
    PRICE_WINDOW_SIZE = 5  # Size of the window for calculating the average price
    TREND_FACTOR = 10  # Adjustment factor for the trend-following strategy

    def __init__(self):
        self.threshold_prices = {
            'AMETHYSTS': {
                'buy': 10000,
                'sell': 10000
            }
        }
        self.price_history = {
            'STARFRUIT': deque()
        }

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        result = {}

        # Update the price history for STARFRUIT
        self.update_price_history(state, 'STARFRUIT')

        # Process AMETHYSTS
        if 'AMETHYSTS' in state.order_depths:
            order_depth: OrderDepth = state.order_depths['AMETHYSTS']
            orders: List[Order] = []
            buy_threshold = self.threshold_prices['AMETHYSTS']['buy']
            sell_threshold = self.threshold_prices['AMETHYSTS']['sell']

            # Check if stop-loss condition is met
            best_bid = max(order_depth.buy_orders, key=lambda price: int(price), default=None)
            if best_bid and int(best_bid) < self.STOP_LOSS_THRESHOLD:
                sell_amount = state.position.get('AMETHYSTS', 0)
                if sell_amount > 0:
                    print(f"STOP-LOSS SELL {sell_amount}x {best_bid}")
                    orders.append(Order('AMETHYSTS', best_bid, -sell_amount))

            # Process regular sell orders if any bid price is higher than the sell threshold
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                if int(best_bid) > sell_threshold:
                    sell_amount = min(best_bid_amount, state.position.get('AMETHYSTS', 0))  # Sell up to the current position
                    if sell_amount > 0:
                        print(f"SELL {sell_amount}x {best_bid}")
                        orders.append(Order('AMETHYSTS', best_bid, -sell_amount))

            # Process regular buy orders if any ask price is lower than the buy threshold
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                if int(best_ask) < buy_threshold:
                    buy_amount = min(best_ask_amount, self.POSITION_LIMIT - state.position.get('AMETHYSTS', 0))  # Buy up to the position limit
                    if buy_amount > 0:
                        print(f"BUY {buy_amount}x {best_ask}")
                        orders.append(Order('AMETHYSTS', best_ask, buy_amount))

            result['AMETHYSTS'] = orders

        # Process STARFRUIT
        if state.timestamp >= 500:
            # Calculate the average price and set the buy and sell thresholds
            avg_price = self.calculate_average_price('STARFRUIT')
            buy_threshold = avg_price - self.TREND_FACTOR
            sell_threshold = avg_price + self.TREND_FACTOR

            if state.timestamp >= 600 and 'STARFRUIT' in state.order_depths:
                order_depth: OrderDepth = state.order_depths['STARFRUIT']
                starfruit_orders: List[Order] = []
                current_position = state.position.get('STARFRUIT', 0)  # Get the current position for STARFRUIT

                # Extract the best bid and best ask
                best_bid = max(order_depth.buy_orders, key=lambda price: int(price), default=None)
                best_ask = min(order_depth.sell_orders, key=lambda price: int(price), default=None)

                # Decide whether to buy or sell based on the threshold prices and position limit
                if best_ask and int(best_ask) < buy_threshold:
                    best_ask_amount = order_depth.sell_orders[best_ask]
                    buy_amount = min(best_ask_amount, self.POSITION_LIMIT - current_position)  # Do not exceed position limit
                    if buy_amount > 0:
                        starfruit_orders.append(Order('STARFRUIT', best_ask, buy_amount))

                elif best_bid and int(best_bid) > sell_threshold:
                    best_bid_amount = order_depth.buy_orders[best_bid]
                    sell_amount = min(best_bid_amount, self.POSITION_LIMIT + current_position)  # Do not exceed position limit
                    if sell_amount > 0:
                        starfruit_orders.append(Order('STARFRUIT', best_bid, -sell_amount))

                result['STARFRUIT'] = starfruit_orders

        # Update the trader state data if needed
        traderData = "SAMPLE"
        conversions = None
        return result, conversions, traderData

    def update_price_history(self, state, symbol):
        if "market_trades" in state.market_trades:
            for trade in state.market_trades["market_trades"].get(symbol, []):
                if symbol == 'STARFRUIT' and state.timestamp >= 500 and not self.price_history[symbol]:
                    self.price_history[symbol] = deque()
                self.price_history[symbol].append(trade['price'])
                if len(self.price_history[symbol]) > self.PRICE_WINDOW_SIZE:
                    self.price_history[symbol].popleft()

    def calculate_average_price(self, symbol):
        if self.price_history[symbol]:
            return sum(self.price_history[symbol]) / len(self.price_history[symbol])
        else:
            return 0