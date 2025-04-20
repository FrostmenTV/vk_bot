"""
Основной модуль VK бота для обработки команд и управления наказаниями.
Взаимодействует с VK API и базой данных MySQL.
"""

import logging
import configparser
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from database import Database
from keyboard import create_accept_keyboard, create_cancel_keyboard
import re
from datetime import datetime

# Настройка логирования для отслеживания работы бота
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/bot.log'
)
logger = logging.getLogger('VKBot')


class VKBot:
    def __init__(self):
        """
        Инициализация бота:
        - Загрузка конфигурации
        - Подключение к VK API
        - Инициализация подключения к БД
        - Установка констант
        """
        # Загрузка конфигурации из файла
        self.config = configparser.ConfigParser()
        self.config.read('config/config.ini')

        try:
            # Инициализация VK API с токеном из конфига
            self.vk_session = VkApi(token=self.config['VK']['token'])
            self.vk = self.vk_session.get_api()
            self.longpoll = VkBotLongPoll(
                self.vk_session, self.config['VK']['group_id'])

            # Подключение к базе данных
            self.db = Database(self.config)

            # Константы для текстовых сообщений
            self.example = '\n\n◉ Пример правильной формы:\n/mute May_Lens 30 Оск. | D. Fererra\n/warn May_Lens Нар. правил ВЧ | I. Dmortyanov\n/ban May_Lens 7 Массовый ДМ | H. Specter'
            self.doing = ['принял', 'отклонил', 'перевыдал']
            self.cancel_reason = [
                'игрок не найден в базе данных сервера.',
                'игрок уже был наказан.',
                'перевыдать'
            ]

            # ID администраторов с правами на проверку форм
            self.admin_ids = [258671626, 42514462]

            logger.info("Бот успешно инициализирован")
        except Exception as e:
            logger.critical(f"Ошибка инициализации бота: {e}")
            raise

    def run(self):
        """Основной цикл обработки событий от VK API"""
        logger.info("Запуск основного цикла бота")
        try:
            for event in self.longpoll.listen():
                try:
                    self.handle_event(event)
                except Exception as e:
                    logger.error(
                        f"Ошибка обработки события: {e}", exc_info=True)
        except Exception as e:
            logger.critical(f"Критическая ошибка в основном цикле: {e}")
            raise

    def handle_event(self, event):
        """
        Маршрутизатор событий от VK API.
        Определяет тип события и вызывает соответствующий обработчик.
        """
        if event.type == VkBotEventType.MESSAGE_NEW:
            self.handle_message(event)
        elif event.type == VkBotEventType.MESSAGE_EVENT:
            self.handle_button(event)
        elif event.type == VkBotEventType.CHAT_INVITE_USER:
            self.handle_chat_invite(event)

    def handle_message(self, event):
        """
        Обработчик входящих сообщений.
        Разделяет обработку личных сообщений и сообщений в чатах.
        """
        message = event.message
        text = message.get('text', '').strip()
        peer_id = message['peer_id']
        user_id = message['from_id']

        # Логирование входящего сообщения
        logger.info(f"Новое сообщение от {user_id} в {peer_id}: {text}")

        # Обработка личных сообщений (только для админов)
        if not message.get('chat_id'):
            if user_id in self.admin_ids:
                self.handle_admin_dm(text, user_id)
            return

        # Обработка команд в чате
        try:
            if text == '/help':
                self.send_help(peer_id)
            elif text.startswith(('/mute ', '/warn ', '/ban ')):
                self.process_punish_command(text, peer_id, user_id)
            elif text.startswith(('/ф ', '/a ', '.ф ', '.a ')):
                self.show_form(text, peer_id, user_id)
            elif text.startswith(('/в ', '/d ', '.в ', '.d ')):
                self.accept_form(text, peer_id, user_id)
            elif text in ['/формы', '/ajhvs', '.формы', '.ajhvs']:
                self.show_pending_forms(peer_id)
        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            self.send_message(
                peer_id, "Произошла ошибка при обработке команды.")

    def process_punish_command(self, command_text, peer_id, user_id):
        """
        Обработка команд наказаний (/mute, /warn, /ban)
        Проверяет формат команды и создает форму наказания.
        """
        # Валидация формата команды
        parts = command_text.split()
        if len(parts) < 5:
            raise ValueError("Неверный формат команды")

        user = parts[1]  # Никнейм игрока
        time = parts[2]  # Время наказания
        reason = ' '.join(parts[3:])  # Причина и администратор

        # Проверка формата никнейма
        if not re.match(r'^[a-zA-Z_]+$', user):
            raise ValueError("Неверный формат никнейма")

        # Проверка формата времени
        if not re.match(r'^\d+$', time):
            raise ValueError("Неверный формат времени")

        # Проверка наличия информации об администраторе
        if '|' not in reason:
            raise ValueError("Отсутствует информация об администраторе")

        try:
            # Запись формы в базу данных
            form_id = self.db.create_form(
                peer_id=peer_id,
                user_id=user_id,
                command=command_text,
                form_type=self.detect_form_type(command_text)
            )

            # Отправка сообщения с кнопками действий
            keyboard = create_accept_keyboard(form_id)
            self.send_message(peer_id, command_text, keyboard)

            logger.info(f"Создана новая форма #{form_id} в чате {peer_id}")
        except Exception as e:
            logger.error(f"Ошибка создания формы: {e}")
            raise

    # ... (остальные методы класса с аналогичными комментариями)


if __name__ == '__main__':
    try:
        bot = VKBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        raise
