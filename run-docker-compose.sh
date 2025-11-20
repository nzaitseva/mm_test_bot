# Скрипт запуска через docker-compose
git clone https://github.com/nzaitseva/mm_test_bot
cd telegram-test-bot

cp .env.example .env    # В .env  BOT_TOKEN и ADMIN_IDS

docker-compose up -d

docker-compose logs -f