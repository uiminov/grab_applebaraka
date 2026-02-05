import asyncio
from collections import defaultdict
from telethon import TelegramClient, events

# ────────────────────────────────────────────────
#                 НАСТРОЙКИ
# ────────────────────────────────────────────────
api_id = 10545599
api_hash = '9e9334b7cb9c5e32e2974a1a67ad0cf2'

source_username = 'telefon_bozor'   # Откуда берем
target_username = 'applebaraka_uzb' # Куда шлем

DELAY = 5.0  # Задержка между отправками

OLD_TEXT = '@Telefon_bozor'
NEW_TEXT = '@applebaraka_uzb'
# ────────────────────────────────────────────────

async def send_post_or_album(client, group, target):
    if not group: return
    group.sort(key=lambda m: m.id)

    caption = ""
    formatting_entities = []
    medias = []

    for m in group:
        if m.media:
            medias.append(m.media)
        if m.message:
            caption = m.message
            formatting_entities = m.entities or []

    # Замена рекламных ссылок
    if OLD_TEXT.lower() in caption.lower():
        # Используем регистронезависимую замену если нужно, 
        # или обычную, как в вашем исходнике:
        caption = caption.replace(OLD_TEXT, NEW_TEXT)

    try:
        if medias:
            await client.send_file(
                target, medias, caption=caption,
                formatting_entities=formatting_entities,
                parse_mode=None, link_preview=False
            )
        elif caption:
            await client.send_message(
                target, caption,
                formatting_entities=formatting_entities,
                parse_mode=None, link_preview=False
            )
        print("✅ Пост успешно переслан")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def main():
    client = TelegramClient('mirror_session', api_id, api_hash)
    await client.start()
    
    source = await client.get_entity(source_username)
    target = await client.get_entity(target_username)

    print(f"🚀 Мониторинг запущен!")
    print(f"Источник: {source.title} --> Цель: {target.title}")

    current_groups = defaultdict(list)
    group_timers = {}

    @client.on(events.NewMessage(chats=source))
    async def handler(event):
        msg = event.message

        # Если это часть альбома
        if msg.grouped_id:
            gid = msg.grouped_id
            current_groups[gid].append(msg)

            # Отменяем старый таймер, если пришло новое фото в ту же группу
            if gid in group_timers:
                group_timers[gid].cancel()

            async def delayed_send():
                await asyncio.sleep(2.0) # Ждем 2 сек, чтобы все фото альбома успели прийти
                grp = current_groups.pop(gid, [])
                if grp:
                    await send_post_or_album(client, grp, target)

            group_timers[gid] = asyncio.create_task(delayed_send())
        
        else:
            # Одиночный пост отправляем сразу
            await send_post_or_album(client, [msg], target)

    print("Ожидание новых постов... (Нажмите Ctrl+C для остановки)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
