PLACEHOLDER_REPLY = "Hello, this is a test response."


def generate_placeholder_reply():
    for word in PLACEHOLDER_REPLY.split(" "):
        yield word
