from dotenv import load_dotenv
import requests
import os
import time
import signal
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

shutdown_requested = False


def handle_shutdown(signum, frame) -> None:
    global shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info(f"Получен сигнал {sig_name}, завершаю работу после текущей итерации...")
    shutdown_requested = True


def check_subscription() -> None:
    token = os.getenv("REMNAWAVE_TOKEN")
    rw_address = os.getenv("REMNAWAVE").rstrip("/")
    ssl_verify = rw_address.startswith("https://")
    rule_name = os.getenv("RULE_NAME")
    header_name = os.getenv("HEADER_NAME")
    github_url = os.getenv("GITHUB_URL")

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If proto is http -> add additional headers
    if not ssl_verify:
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-For"] = "127.0.0.1"

    # Fetch data from panel 
    panel_response = requests.get(f"{rw_address}/api/subscription-settings", headers=headers)
    panel_response.raise_for_status()

    data = panel_response.json()["response"]
    rules = data["responseRules"]["rules"]
    rule = next((r for r in rules if r["name"] == rule_name), None)

    if rule is None:
        logger.warning(f"Правило '{rule_name}' не найдено в панели")
        return

    mod_headers = rule.get("responseModifications", {}).get("headers", [])
    header_entry = next((h for h in mod_headers if h["key"] == header_name), None)

    if header_entry is None:
        logger.warning(f"Заголовок '{header_name}' не найден в правиле '{rule_name}'")
        return

    current_value = header_entry["value"]

    # Fetch data from github
    github_response = requests.get(github_url)
    github_response.raise_for_status()
    new_value = github_response.text.strip()

    if current_value.strip() == new_value:
        logger.info("Совпадают, изменений не требуется")
        return

    logger.info("Значения отличаются, обновляю панель")
    logger.info(f"Было: {current_value}")
    logger.info(f"Стало: {new_value}")

    header_entry["value"] = new_value

    patch_response = requests.patch(
        f"{rw_address}/api/subscription-settings",
        headers=headers,
        json=data
    )
    patch_response.raise_for_status()

    logger.info("Панель успешно обновлена")


def main() -> None:
    load_dotenv()

    interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info(f"Сервис запущен, интервал проверки: {interval} сек")

    while not shutdown_requested:
        try:
            check_subscription()
        except Exception as e:
            logger.error(f"ошибка во время проверки: {e}")

        for _ in range(interval):
            if shutdown_requested:
                break
            time.sleep(1)
            
    logger.info("Сервис остановлен")


if __name__ == "__main__":
    main()
