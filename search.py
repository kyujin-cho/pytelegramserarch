from motor import motor_asyncio
from telethon import TelegramClient
from telethon.tl.types import PeerChannel
from telethon.tl.custom import message
from typing import List
from asyncio import run, get_event_loop, set_event_loop, new_event_loop
import click
import sys
import re
import signal
import functools


API_ID = '17656'
API_HASH = 'f311386142ab9bef2851faeefc7d4ba9'

def print_if_found(dicted: dict, kwd: re.Pattern) -> int:
    '''Call mprint() if given pattern is found from dicted
    :param dict dicted: Message serialized to dictionary
    :param re.Pattern kwd: pattern to search inside message
    :returns: start position if found, -1 if not found
    '''

    msg = dicted['message']
    chatId = dicted['id']

    if type(msg) != str:
        return -1

    m = kwd.search(msg)
    if m != None:
        start, end = m.span()
        mprint(msg, start, end, chatId)
        return start
    return -1

def mprint(msg: str, start: int, end: int, chatId: int):
    '''Prints abstracted message
    :param str msg: Message to print
    :param int start: Keyword start location
    :param int end: Keyword end location
    :param int chatId: Chat ID
    '''

    abstract = '...' + msg[start-4:start] + msg[start:end+1] + msg[end+1:end+5] + '...'
    print(f'found at chatId {chatId}: {abstract}')

def rmprint(dicted: dict):
    '''Prints full message
    :param dict dicted: Message serialized to dictionary
    '''

    chatId = dicted['id']
    msg = dicted['message']
    print(f'found at chatId {chatId}: {msg}')
    return msg

def message_to_dict(msg: message.Message) -> dict:
    '''Converts telethon Message to dictionary. 
    Required when inserting into mongodb collection since Message object is not serializable to BSON.

    :param message.Message msg: Message object to serialize
    :returns: Serialized dictionary
    '''
    
    msg.to_dict()
    return {
        'id': msg.id,
        'mentioned': msg.mentioned,
        'to_id': msg.to_id.to_dict() if isinstance(msg.to_id, PeerChannel) else str(msg.to_id),
        'date': msg.date,
        'reply_to_msg_id': msg.reply_to_msg_id,
        'from_id': msg.from_id,
        'message': msg.message
    }

async def search(chat_id: str, kwd: str, from_cache: bool=False, dump: bool=False):
    client = TelegramClient('search_sess', API_ID, API_HASH)
    await client.start()
    mongo = motor_asyncio.AsyncIOMotorClient()
    collection = mongo.tele_db.messages

    # Try to find from cached messages in MongoDB
    from_cached = collection.find( { 'message': { '$regex': kwd } } ).sort([('id', 1)])
    await from_cached.fetch_next
    first_msg = from_cached.next_object()

    if first_msg != None:
        rmprint(first_msg)
        while (await from_cached.fetch_next):
            message = from_cached.next_object()
            rmprint(message)
            if dump:
                chatId = message['id']
                msg = message['message']
                fw.write(f'{chatId}:{msg}\n')
    
    # Stop if from_cache option enabled
    if from_cache:
        if dump:
            fw.close()
        return

    # Compile regex pattern to re.Pattern object
    kwd = re.compile(kwd)
    
    # Fetch latest cached message ID; then only find newer messages than this message
    latest_cursor = collection.find({}).sort([('id', -1)])
    await latest_cursor.fetch_next
    latest_msg = latest_cursor.next_object()

    entity = await client.get_entity(chat_id)
    fetched, found = 0, 0

    print()

    if latest_msg != None:
        latest_id = latest_msg['id']
        # Check latest uncached message first
        async for server_message in client.iter_messages(entity, min_id=latest_id):
            dicted = message_to_dict(server_message)
            chatId = dicted['id']
            fetched += 1
            sys.stdout.write(u'\u001b[1A')
            sys.stdout.write(u'\u001b[2K')
            sys.stdout.flush()

            print(f'Fetched {fetched} ({chatId}); found {found} messages')
            if found > 0:
                sys.stdout.write(u'\u001b[' + str(found) + 'B')
                sys.stdout.flush()

            # Add fetched message object to MongoDB collection
            await collection.insert_one(dicted)
            index = print_if_found(dicted, kwd)

            if index != -1:
                found += 1
                if dump:
                    message = dicted['message']
                    fw.write(f'{chatId}:{message}\n')

            if found > 0:
                sys.stdout.write(u'\u001b[' + str(found) + 'A')
            sys.stdout.flush()

    first_id = first_msg['id'] if first_msg else 0
    # Then fetch messages uncached previously
    async for server_message in client.iter_messages(entity, offset_id=first_id):
        dicted = message_to_dict(server_message)
        chatId = dicted['id']
        fetched += 1
        sys.stdout.write(u'\u001b[1A')
        sys.stdout.write(u'\u001b[2K')
        sys.stdout.flush()

        print(f'Fetched {fetched} ({chatId}); found {found} messages')
        if found > 0:
            sys.stdout.write(u'\u001b[' + str(found) + 'B')
            sys.stdout.flush()

        await collection.insert_one(dicted)
        index = print_if_found(dicted, kwd)

        if index != -1:
            found += 1
            if dump:
                message = dicted['message']
                fw.write(f'{chatId}:{message}\n')

        if found > 0:
            sys.stdout.write(u'\u001b[' + str(found) + 'A')
        sys.stdout.flush()

# SIGINT HANDLER
def signal_handler(name):
    if fw != None:
        fw.close()
    exit()

fw = None

@click.command()
@click.option('-c', '--from-cache', is_flag=True, help='Flag if you want to search from MongoDB cache.')
@click.option('-d', '--dump', help='Dumps searched messages to given filename.')
@click.argument('chat-id')
def main(from_cache, chat_id, dump):
    global fw
    reg = input('Regex: ')
    if dump:
        fw = open(dump, 'w')

    loop = new_event_loop()
    set_event_loop(loop)
    loop.add_signal_handler(signal.SIGINT, functools.partial(signal_handler, name='SIGINT'))

    loop.run_until_complete(search(chat_id, reg, from_cache=from_cache, dump=dump))
    # run()

if __name__ == '__main__':
    main()