import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions,
            "",
            "",
        ]))

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.price,
                    trade.quantity,
                    trade.buyer,
                    trade.seller,
                    trade.timestamp,
                ])

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[:max_length - 3] + "..."

logger = Logger()

from datamodel import OrderDepth, Order, TradingState
from typing import List, Tuple, Dict

from typing import List


class Trader:
    POSITION_LIMIT = 20  # The maximum absolute value of the position
    STOP_LOSS_THRESHOLD = 9500  # Set a stop-loss threshold for AMETHYSTS
    FORECAST_WINDOW_SIZE = 500  # Number of timestamps to use for forecasting
    SHORT_TERM_SMA_WINDOW = 50  # Short-term SMA window
    LONG_TERM_SMA_WINDOW = 200  # Long-term SMA window

    def __init__(self):
        self.threshold_prices = {
            'AMETHYSTS': {
                'buy': 8500,
                'sell': 11000
            },
            'STARFRUIT': {
                'buy': 4980,
                'sell': 5000
            }
        }
        self.starfruit_prices = []

    def calculate_sma(self, prices, window):
        if len(prices) < window:
            return None
        return sum(prices[-window:]) / window

    def run(self, state: TradingState):
        result = {}

        # Check if traderData attribute exists in TradingState
        if hasattr(state, 'traderData'):
            print("traderData: " + state.traderData)
        else:
            print("traderData attribute not found in TradingState")

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
                    print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order('AMETHYSTS', best_bid, best_bid_amount))  # Selling all available volume

            # Process regular buy orders if any ask price is lower than the buy threshold
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                if int(best_ask) < buy_threshold:
                    print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order('AMETHYSTS', best_ask, -best_ask_amount))  # Buying all available volume

            result['AMETHYSTS'] = orders

        # Process STARFRUIT
        if 'STARFRUIT' in state.order_depths:
            order_depth: OrderDepth = state.order_depths['STARFRUIT']
            starfruit_orders: List[Order] = []
            current_position = state.position.get('STARFRUIT', 0)  # Get the current position for STARFRUIT
            buy_threshold = self.threshold_prices['STARFRUIT']['buy']
            sell_threshold = self.threshold_prices['STARFRUIT']['sell']

            # Extract the best bid and best ask
            best_bid = max(order_depth.buy_orders, key=lambda price: int(price), default=None)
            best_ask = min(order_depth.sell_orders, key=lambda price: int(price), default=None)

            # Add current price to historical data for STARFRUIT
            current_price = int(best_bid) if best_bid else int(best_ask)
            self.starfruit_prices.append(current_price)

            # Calculate short-term and long-term SMAs
            short_term_sma = self.calculate_sma(self.starfruit_prices, self.SHORT_TERM_SMA_WINDOW)
            long_term_sma = self.calculate_sma(self.starfruit_prices, self.LONG_TERM_SMA_WINDOW)

            # Determine trend based on SMAs
            if short_term_sma and long_term_sma:
                if short_term_sma > long_term_sma:
                    # print("STARFRUIT is trending upward (Bullish)")
                    # Implement your buying logic here based on the upward trend
                    if best_ask and int(best_ask) < buy_threshold:
                        best_ask_amount = order_depth.sell_orders[best_ask]
                        buy_amount = min(best_ask_amount,
                                         self.POSITION_LIMIT - current_position)  # Do not exceed position limit
                        if buy_amount > 0:
                            starfruit_orders.append(Order('STARFRUIT', best_ask, buy_amount))

                elif short_term_sma < long_term_sma:
                    # print("STARFRUIT is trending downward (Bearish)")
                    # Implement your selling logic here based on the downward trend
                    if best_bid and int(best_bid) > sell_threshold:
                        best_bid_amount = order_depth.buy_orders[best_bid]
                        sell_amount = min(best_bid_amount,
                                          self.POSITION_LIMIT + current_position)  # Do not exceed position limit
                        if sell_amount > 0:
                            starfruit_orders.append(Order('STARFRUIT', best_bid, -sell_amount))

            result['STARFRUIT'] = starfruit_orders

        # Update the trader state data if needed
        conversions = None  # Placeholder for conversions value
        return result, conversions
