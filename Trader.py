from collections import deque
from datamodel import TradingState, Order

class Trader:
    POSITION_LIMIT = 20
    STOP_LOSS_THRESHOLD = 9500
    PRICE_WINDOW_SIZE = 10
    AMETHYSTS_BUY_RANGE = range(9996, 10000)
    AMETHYSTS_SELL_RANGE = range(10000, 10004)

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
        self.price_history = {
            'STARFRUIT': deque(),
            'AMETHYSTS': deque()
        }

    def initialize_price_history(self, historical_data, symbol):
        price_history = []
        for row in historical_data:
            for trade in row['market_trades'][symbol]:
                price_history.append(trade['price'])
        self.price_history[symbol] = deque(price_history[-self.PRICE_WINDOW_SIZE:])

    def run(self, state: TradingState):
        orders = {
            'AMETHYSTS': [],
            'STARFRUIT': []
        }
        conversions = {}
        for symbol in ['AMETHYSTS', 'STARFRUIT']:
            self.update_price_history(state, symbol)
            symbol_orders = self.get_orders(state, symbol)
            orders[symbol].extend(symbol_orders)
        return orders, conversions, {}

    def update_price_history(self, state, symbol):
        if "market_trades" in state.market_trades:
            for trade in state.market_trades["market_trades"].get(symbol, []):
                self.price_history[symbol].append(trade.price)
                if len(self.price_history[symbol]) > self.PRICE_WINDOW_SIZE:
                    self.price_history[symbol].popleft()

    def get_orders(self, state, symbol):
        orders = []
        position = state.position.get(symbol, 0)

        # Получаем символы в order_depths
        symbols_in_order_depths = list(state.order_depths.keys())

        # Если символ присутствует в order_depths, используем его
        if symbol in symbols_in_order_depths:
            order_depth = state.order_depths[symbol]
        # Иначе, используем первый символ из order_depths (если он есть)
        elif symbols_in_order_depths:
            order_depth = state.order_depths[symbols_in_order_depths[0]]
        # Если order_depths пустой, возвращаем пустой список заказов
        else:
            return orders

        if position == 0:
            buy_prices = [price for price in self.AMETHYSTS_BUY_RANGE if str(price) in order_depth.buy_orders]
            if buy_prices:
                buy_price = max(buy_prices)
                orders.append(Order(symbol, buy_price, self.POSITION_LIMIT))

        elif position > 0:
            sell_prices = [price for price in self.AMETHYSTS_SELL_RANGE if str(price) in order_depth.sell_orders]
            if sell_prices:
                sell_price = min(sell_prices)
                orders.append(Order(symbol, sell_price, position))

        return orders