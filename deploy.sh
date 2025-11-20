#!/bin/bash


case "$1" in
    start)
        docker-compose up -d
        echo "✅ Бот запущен"
        ;;
    stop)
        docker-compose down
        echo "🛑 Бот остановлен"
        ;;
    restart)
        docker-compose restart
        echo "🔄 Бот перезапущен"
        ;;
    logs)
        docker-compose logs -f
        ;;
    update)
        git pull
        docker-compose build --no-cache
        docker-compose up -d
        echo "🎉 Бот обновлен"
        ;;
    backup)
        docker-compose exec telegram-bot python export_data.py --type all
        echo "📦 Бэкап создан"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|logs|update|backup}"
        exit 1
        ;;
esac