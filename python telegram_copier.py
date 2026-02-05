import asyncio
from collections import defaultdict
from telethon import TelegramClient, events

# ────────────────────────────────────────────────
#               НАСТРОЙКИ — ИЗМЕНИТЕ ЗДЕСЬ
# ────────────────────────────────────────────────

api_id = 10545599
api_hash = '9e9334b7cb9c5e32e2974a1a67ad0cf2'

source_username = 'telefon_bozor'       # без @
target_username = 'applebaraka_uzb'     # без @

DELAY = 5.0                             # секунды между отправками постов

OLD_TEXT = '@Telefon_bozor'
NEW_TEXT = '@applebaraka_uzb'

# ────────────────────────────────────────────────

async def send_post_or_album(client, group, target):
    """
    Универсальная отправка: одиночный пост или альбом
    """
    if not group:
        return

    group.sort(key=lambda m: m.id)

    caption = ""
    formatting_entities = []
    medias = []

    # Собираем подпись и медиа
    # Обычно подпись бывает только в первом или последнем сообщении альбома
    for m in group:
        if m.media:
            medias.append(m.media)
        if m.message:
            caption = m.message
            formatting_entities = m.entities or []

    # Замена текста (если есть что менять)
    if OLD_TEXT in caption:
        caption = caption.replace(OLD_TEXT, NEW_TEXT)
        print("Замена выполнена в подписи:", caption[:60] + "..." if len(caption) > 60 else caption)

    # Отправляем
    try:
        if medias:
            # Альбом или пост с медиа
            await client.send_file(
                target,
                medias,
                caption=caption,
                formatting_entities=formatting_entities,
                parse_mode=None,
                reply_markup=None,
                link_preview=False,
                force_document=False
            )
        elif caption:
            # Только текст
            await client.send_message(
                target,
                caption,
                formatting_entities=formatting_entities,
                parse_mode=None,
                reply_markup=None,
                link_preview=False
            )
        else:
            print("Пропущен пустой пост")
            return

        print("Отправлено успешно")
    except Exception as e:
        print("Ошибка при отправке:", type(e).__name__, str(e))


async def main():
    client = TelegramClient('mirror_session', api_id, api_hash)

    await client.start()
    print("Клиент запущен. Авторизуйтесь если требуется.")

    source = await client.get_entity(f'@{source_username}')
    target = await client.get_entity(f'@{target_username}')

    print(f"Источник: {source.title}  |  Цель: {target.title}")

    # ──────── Загрузка и отправка последних 200 постов ────────
    print("Загружаю последние 200 сообщений...")

    messages = await client.get_messages(source, limit=200)
    messages.reverse()  # от старых к новым

    grouped = defaultdict(list)

    for msg in messages:
        key = msg.grouped_id if msg.grouped_id else msg.id
        grouped[key].append(msg)

    sent_count = 0

    for group in grouped.values():
        await send_post_or_album(client, group, target)
        sent_count += 1
        print(f"Отправлен пост {sent_count} / {len(grouped)}   (группа из {len(group)} сообщений)")
        await asyncio.sleep(DELAY)

    print(f"Историческая часть завершена ({sent_count} постов отправлено)")

    # ──────── Мониторинг новых сообщений ────────

    last_id = max((m.id for m in messages), default=0) if messages else 0

    current_groups = defaultdict(list)
    group_timers = {}

    @client.on(events.NewMessage(chats=source))
    async def handler(event):
        nonlocal last_id

        msg = event.message

        if msg.id <= last_id:
            return

        last_id = msg.id

        if msg.grouped_id:
            gid = msg.grouped_id
            current_groups[gid].append(msg)

            # Перезапуск таймера на отправку альбома
            if gid in group_timers:
                group_timers[gid].cancel()

            async def delayed_send():
                await asyncio.sleep(1.8)  # время на сбор всего альбома
                grp = current_groups.pop(gid, [])
                if grp:
                    await send_post_or_album(client, grp, target)
                    await asyncio.sleep(DELAY)

            task = asyncio.create_task(delayed_send())
            group_timers[gid] = task

        else:
            # Одиночный пост
            await send_post_or_album(client, [msg], target)
            await asyncio.sleep(DELAY)

    print("Мониторинг новых постов запущен. Ctrl+C — остановка.")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())