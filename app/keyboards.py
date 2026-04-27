# keyboards.py
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


class MainMenuKeyboards:

    @staticmethod
    def create_main_menu_keyboard():
        """Клавиатура для главного меню"""
        builder = InlineKeyboardBuilder()

        # Первая строка: одна кнопка
        builder.row(
            CallbackButton(
                text='📝 Создать обращение',
                payload='process_data'
            )
        )

        # Вторая строка: две кнопки
        builder.row(
            CallbackButton(
                text='💬 Комментарий',
                payload='comment_task'
            ),
            CallbackButton(
                text='❌ Отмена заявки',
                payload='cancel_request'
            )
        )

        # Третья строка: одна кнопка
        builder.row(
            CallbackButton(
                text='📁 Закрытые задачи',
                payload='closed_tasks'
            )
        )

        # Четвертая строка: две кнопки в ряд
        builder.row(
            CallbackButton(
                text='📞 Контакты',
                payload='contacts_info'
            ),
            CallbackButton(
                text='ℹ️ О нас',
                payload='company_info'
            )
        )

        return builder.as_markup()

    @staticmethod
    def create_back_to_menu_keyboard():
        """Клавиатура для возвращения в главное меню"""
        builder = InlineKeyboardBuilder()

        builder.row(
            CallbackButton(
                text='🔙 Вернуться в меню',
                payload='back_to_main_menu'
            )
        )

        return builder.as_markup()


    @staticmethod
    def create_confirmation_keyboard():
        """Клавиатура для подтверждения действия"""
        builder = InlineKeyboardBuilder()

        builder.row(
            CallbackButton(
                text='✅ Подтвердить',
                payload='confirm_action'
            ),
            CallbackButton(
                text='❌ Отмена',
                payload='cancel_action'
            )
        )

        return builder.as_markup()

    @staticmethod
    def create_go_to_menu_keyboard():
        """Клавиатура с кнопкой перехода в главное меню"""
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(
                text='🏠 Перейти в главное меню',
                payload='back_to_main_menu'
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_pre_inn_keyboard():
        """Экран перед вводом ИНН"""
        builder = InlineKeyboardBuilder()

        builder.row(
            CallbackButton(
                text='✅ Информация прочитана',
                payload='start_inn_input'
            )
        )

        builder.row(
            CallbackButton(
                text='🏠 Главное меню',
                payload='back_to_main_menu'
            )
        )

        return builder.as_markup()

from maxapi.types.attachments.buttons import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


class CreateTaskKeyboards:

    @staticmethod
    async def build_themes_task_keyboard(items):
        builder = InlineKeyboardBuilder()

        for item in items:
            item_id = item.get("item_id")
            value = item.get("values")[0]

            builder.row(
                CallbackButton(
                    text=f"💻 {value}",
                    payload=f"theme:{item_id}:{value}"
                )
            )

        builder.row(
            CallbackButton(
                text="↩️ Вернуться в главное меню",
                payload="back_to_main_menu"
            )
        )

        return builder.as_markup()