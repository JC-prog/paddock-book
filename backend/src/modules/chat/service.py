import asyncio

PLACEHOLDER_REPLY = "Hello, this is a test response."
WORD_DELAY_SECONDS = 0.15


async def generate_placeholder_reply():
    words = PLACEHOLDER_REPLY.split(" ")
    for index, word in enumerate(words):
        if index > 0:
            await asyncio.sleep(WORD_DELAY_SECONDS)
        yield word
