import json
from datamodel import Order, ProsperityEncoder, Symbol, TradingState, Trade
from typing import Any

class Logger:
    # Set this to true, if u want to create
    # local logs
    local: bool 
    # this is used as a buffer for logs
    # instead of stdout
    local_logs: dict[int, str] = {}

    def __init__(self, local=False) -> None:
        self.logs = ""
        self.local = local

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        output = json.dumps({
            "state": state,
            "orders": orders,
            "logs": self.logs,
        }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True)
        if self.local:
            self.local_logs[state.timestamp] = output
        print(output)

        self.logs = ""

    def compress_state(self, state: TradingState) -> dict[str, Any]:
        listings = []
        for listing in state.listings.values():
            listings.append([listing["symbol"], listing["product"], listing["denomination"]])

        order_depths = {}
        for symbol, order_depth in state.order_depths.items():
            order_depths[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return {
            "t": state.timestamp,
            "l": listings,
            "od": order_depths,
            "ot": self.compress_trades(state.own_trades),
            "mt": self.compress_trades(state.market_trades),
            "p": state.position,
            "o": state.observations,
        }

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.buyer,
                    trade.seller,
                    trade.price,
                    trade.quantity,
                    trade.timestamp,
                ])

        return compressed

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

# This is provisionary, if no other algorithm works.
# Better to loose nothing, then dreaming of a gain.
from collections import deque
from typing import List


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

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
from collections import deque

class Trader:
    POSITION_LIMIT = 20  # The maximum absolute value of the position
    STOP_LOSS_THRESHOLD = 9500  # Set a stop-loss threshold for AMETHYSTS
    PRICE_WINDOW_SIZE = 10  # Size of the window for calculating the average price

    def __init__(self):
        self.threshold_prices = {
            'AMETHYSTS': {
                'buy': 9990,
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

            # Calculate the average price and set the buy and sell thresholds
            avg_price = self.calculate_average_price('STARFRUIT')
            buy_threshold = avg_price - 100  # Buy if the price is 100 below the average
            sell_threshold = avg_price + 100  # Sell if the price is 100 above the average

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
        conversions = None  # Placeholder for conversions value
        return result, conversions, traderData

    def update_price_history(self, state, symbol):
        if "market_trades" in state.market_trades:
            for trade in state.market_trades["market_trades"].get(symbol, []):
                self.price_history[symbol].append(trade['price'])
                if len(self.price_history[symbol]) > self.PRICE_WINDOW_SIZE:
                    self.price_history[symbol].popleft()

    def calculate_average_price(self, symbol):
        if self.price_history[symbol]:
            return sum(self.price_history[symbol]) / len(self.price_history[symbol])
        else:
            return 0