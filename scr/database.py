"""
Модуль для работы с базой данных MySQL.
Обеспечивает подключение и выполнение запросов.
"""

import mysql.connector
from mysql.connector import pooling
import logging

logger = logging.getLogger('Database')


class Database:
    def __init__(self, config):
        """
        Инициализация подключения к базе данных.
        Создает пул соединений на основе конфигурации.

        :param config: Конфигурация подключения к БД
        """
        self.config = config
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="vk_bot_pool",
                pool_size=int(self.config['Database']['pool_size']),
                host=self.config['Database']['host'],
                user=self.config['Database']['user'],
                password=self.config['Database']['password'],
                database=self.config['Database']['database'],
                autocommit=True
            )
            logger.info("Пул соединений с БД успешно создан")
        except Exception as e:
            logger.critical(f"Ошибка создания пула соединений: {e}")
            raise

    def execute(self, query, params=None):
        """
        Выполняет SQL запрос и возвращает результат.

        :param query: SQL запрос
        :param params: Параметры запроса
        :return: Результат запроса (для SELECT) или ID вставленной записи
        """
        conn = None
        try:
            conn = self.pool.get_connection()
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())

                # Для SELECT возвращаем результаты
                if query.strip().lower().startswith('select'):
                    return cursor.fetchall()

                # Для других запросов возвращаем ID последней записи
                return cursor.lastrowid
        except Exception as e:
            logger.error(
                f"Ошибка выполнения запроса: {e}\nQuery: {query}\nParams: {params}")
            raise
        finally:
            if conn:
                conn.close()

    def create_form(self, peer_id, user_id, command, form_type):
        """
        Создает новую форму наказания в базе данных.

        :param peer_id: ID чата
        :param user_id: ID отправителя
        :param command: Текст команды
        :param form_type: Тип наказания
        :return: ID созданной формы
        """
        query = """
        INSERT INTO forms 
        (chat_id, send_id, type, context, date_send) 
        VALUES (%s, %s, %s, %s, NOW())
        """
        return self.execute(query, (peer_id, user_id, form_type, command))

    def get_form(self, form_id, chat_id=None):
        """
        Получает информацию о форме по ID.

        :param form_id: ID формы
        :param chat_id: ID чата (опционально для проверки принадлежности)
        :return: Данные формы или None если не найдена
        """
        if chat_id:
            query = "SELECT * FROM forms WHERE id = %s AND chat_id = %s"
            params = (form_id, chat_id)
        else:
            query = "SELECT * FROM forms WHERE id = %s"
            params = (form_id,)

        result = self.execute(query, params)
        return result[0] if result else None

    def update_form_status(self, form_id, status, result=None, user_id=None):
        """
        Обновляет статус формы в базе данных.

        :param form_id: ID формы
        :param status: Новый статус (1 - принята, 2 - отклонена)
        :param result: Причина отклонения (опционально)
        :param user_id: ID пользователя, изменившего статус
        :return: Количество измененных строк
        """
        query = """
        UPDATE forms 
        SET state = %s, result = %s, receive_id = %s, date = NOW() 
        WHERE id = %s
        """
        return self.execute(query, (status, result, user_id, form_id))

    # Другие методы работы с БД...
