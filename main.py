import time
from src.trader.trader import Trader
from src.utils.logger import get_logger

logger = get_logger("main")

INTERVAL_SECONDS = 60 * 60  # 1시간마다 실행


def main():
    logger.info("업비트 자동매매 시작")
    trader = Trader()

    while True:
        try:
            trader.run_once()
        except Exception as e:
            logger.error(f"오류 발생: {e}")

        logger.info(f"{INTERVAL_SECONDS // 60}분 후 재실행")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
