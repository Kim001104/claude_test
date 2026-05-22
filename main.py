import schedule
import time
from src.trader.trader import Trader
from src.utils.logger import get_logger

logger = get_logger("main")
trader = Trader()

# 5분마다 가격 감시 (급등/급락 즉시 대응)
schedule.every(5).minutes.do(trader.check_price_alarm)

# 전략 판단: 한국 시간 기준 하루 6번 (서버 UTC 기준)
schedule.every().day.at("00:00").do(trader.run_once)  # KST 09:00
schedule.every().day.at("03:00").do(trader.run_once)  # KST 12:00
schedule.every().day.at("06:00").do(trader.run_once)  # KST 15:00
schedule.every().day.at("09:00").do(trader.run_once)  # KST 18:00
schedule.every().day.at("12:00").do(trader.run_once)  # KST 21:00
schedule.every().day.at("15:00").do(trader.run_once)  # KST 00:00

logger.info("봇 시작. 5분 감시 + 한국 시간 09:00/12:00/15:00/18:00/21:00/00:00 전략 실행.")
while True:
    schedule.run_pending()
    time.sleep(60)
